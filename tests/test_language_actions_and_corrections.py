import base64
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from catnanny.services.profile_service import cats
from catnanny.storage.repositories import get_event,list_event_photos

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aRZkAAAAASUVORK5CYII=')


def send(client,text,session=None,**fields):
    return client.post('/conversations/turns',json={'request_id':uuid4().hex,'text':text,'session_id':session,**fields})


def seed(client):
    return send(client,'',cat_id='mochi',event_type='vomit',details={'content':'food','episode_count':2,'has_blood':False,'low_energy':False}).json()


def test_screenshot_correction_unknown_lowercase_cat_moves_existing_record(isolated_db,monkeypatch):
    from app import app
    from catnanny.services import photo_service
    monkeypatch.setattr(photo_service,'UPLOAD_DIR',isolated_db.DATA_DIR/'uploads')
    with TestClient(app) as client:
        original=send(client,'',cat_id='mochi',event_type='vomit',details={'content':'food','episode_count':6,'has_blood':False,'low_energy':True}).json()
        photo=client.post('/photos/upload',data={'event_id':original['event_id']},files={'photo':('photo.png',PNG,'image/png')}).json()['photo']
        correction=send(client,'no actually it is for jeremy, vomit today and already saw 6 times in 3 days',original['session_id']).json()
        assert correction['status']=='awaiting_confirmation'
        assert 'jeremy' in correction['speech'].lower()
        assert get_event(original['event_id']).cat_id=='mochi'
        moved=send(client,'Yes',original['session_id']).json()
        assert moved['cat_name'].casefold()=='jeremy'
        assert moved['ui_action']=='observation_reassigned'
        assert moved['event_id']==original['event_id']
        assert moved['details']==original['details']
        assert list_event_photos(original['event_id'])[0].cat_id==moved['cat_id']
        assert client.get('/reports/vet-summary?cat_id=mochi').json()['counts']['total_events']==0
        report=client.get('/reports/vet-summary',params={'cat_id':moved['cat_id']}).json()
        assert report['counts']['total_events']==1
        assert report['timeline'][0]['photos']==[photo['url']]


@pytest.mark.parametrize('text',[
    'no actually it is for jeremy, vomit today and already saw 6 times in 3 days',
    "No, actually it's for Jeremy.",
    'Actually this is about Jeremy, not Mochi.',
    'No actually it was for Jeremy.',
])
def test_colloquial_correction_known_cat_keeps_same_event(isolated_db,text):
    from app import app
    with TestClient(app) as client:
        target=client.post('/cats',json={'name':'Jeremy'}).json()
        original=seed(client)
        corrected=send(client,text,original['session_id']).json()
        assert corrected['cat_id']==target['cat_id']
        assert corrected['ui_action']=='observation_reassigned'
        assert corrected['event_id']==original['event_id']
        assert corrected['details']==original['details']


def test_user_misspoke_unknown_cat_confirm_create_and_move_same_event_and_photo(isolated_db,monkeypatch):
    from app import app
    from catnanny.services import photo_service
    monkeypatch.setattr(photo_service,'UPLOAD_DIR',isolated_db.DATA_DIR/'uploads')
    with TestClient(app) as client:
        unrelated=seed(client)
        original=seed(client)
        original_event=get_event(original['event_id'])
        photo=client.post('/photos/upload',data={'event_id':original['event_id']},files={'photo':('photo.png',PNG,'image/png')}).json()['photo']
        correction=send(client,'Actually I meant Jeremy, not Mochi.',original['session_id']).json()
        assert correction['status']=='awaiting_confirmation'
        assert correction['event_id']==original['event_id']
        assert get_event(original['event_id']).cat_id=='mochi'
        assert not any(cat['name']=='Jeremy' for cat in cats())
        request={'request_id':'confirm-once','session_id':original['session_id'],'text':'Yes'}
        moved=client.post('/conversations/turns',json=request).json()
        assert moved['cat_name']=='Jeremy'
        assert moved['ui_action']=='observation_reassigned'
        assert moved['session_id']==original['session_id']
        assert moved['event_id']==original['event_id']
        assert moved['details']==original['details']
        corrected_event=get_event(original['event_id'])
        assert corrected_event.ts==original_event.ts
        assert corrected_event.reporter==original_event.reporter
        assert corrected_event.cat_id==moved['cat_id']
        attached=list_event_photos(original['event_id'])[0]
        assert attached.cat_id==moved['cat_id'] and attached.url==photo['url']
        assert client.get('/reports/vet-summary?cat_id=mochi').json()['counts']['total_events']==1
        report=client.get('/reports/vet-summary',params={'cat_id':moved['cat_id']}).json()
        assert report['counts']['total_events']==1 and report['timeline'][0]['photos']==[photo['url']]
        assert get_event(unrelated['event_id']).cat_id=='mochi'
        assert client.post('/conversations/turns',json=request).json()==moved
        with isolated_db.get_connection() as conn:
            assert conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]==2
            assert conn.execute('SELECT COUNT(*) FROM event_reassignments').fetchone()[0]==1


def test_known_target_correction_is_not_a_new_cat_switch(isolated_db):
    from app import app
    with TestClient(app) as client:
        target=client.post('/cats',json={'name':'Jeremy'}).json()
        original=seed(client)
        corrected=send(client,'Actually it was Jeremy.',original['session_id']).json()
        assert corrected['cat_id']==target['cat_id']
        assert corrected['session_id']==original['session_id']
        assert corrected['event_id']==original['event_id']
        assert client.get('/events?cat_id=mochi').json()['total']==0


def test_chinese_subject_correction_and_cancellation(isolated_db):
    from app import app
    with TestClient(app) as client:
        original=seed(client)
        correction=send(client,'实际上我讲的是Jeremy，不是Mochi',original['session_id']).json()
        assert correction['status']=='awaiting_confirmation'
        cancelled=send(client,'No',original['session_id']).json()
        assert cancelled['status']=='completed'
        assert get_event(original['event_id']).cat_id=='mochi'
        assert len(cats())==1


def test_atomic_reassignment_rolls_back_profile_event_and_photo_on_failure(isolated_db,monkeypatch):
    from app import app
    from catnanny.services import photo_service
    monkeypatch.setattr(photo_service,'UPLOAD_DIR',isolated_db.DATA_DIR/'uploads')
    with TestClient(app,raise_server_exceptions=False) as client:
        original=seed(client)
        client.post('/photos/upload',data={'event_id':original['event_id']},files={'photo':('photo.png',PNG,'image/png')})
        send(client,'I meant Jeremy',original['session_id'])
        with isolated_db.get_connection() as conn:
            conn.execute("CREATE TRIGGER fail_photo_move BEFORE UPDATE OF cat_id ON photos BEGIN SELECT RAISE(ABORT,'test failure'); END")
        assert send(client,'Yes',original['session_id']).status_code==500
        assert get_event(original['event_id']).cat_id=='mochi'
        assert list_event_photos(original['event_id'])[0].cat_id=='mochi'
        assert not any(cat['name']=='Jeremy' for cat in cats())
        with isolated_db.get_connection() as conn:
            assert conn.execute('SELECT COUNT(*) FROM event_reassignments').fetchone()[0]==0


def test_language_equivalents_for_management_controls(isolated_db):
    from app import app
    with TestClient(app) as client:
        added=send(client,'Add a cat named Jeremy.').json()
        assert added['cat_name']=='Jeremy' and added['ui_action']=='profiles_updated'
        speaker=send(client,'I am Sam.',added['session_id']).json()
        assert speaker['caregiver_name']=='Sam'
        logged=send(client,'Jeremy vomited food once.',speaker['session_id']).json()
        assert logged['caregiver_name']=='Sam'
        assert get_event(logged['event_id']).reporter=='Sam'
        report=send(client,"Show me Jeremy's care report for the last 7 days.",logged['session_id']).json()
        assert report['ui_action']=='open_report' and report['action_payload']['report_days']==7
        log=send(client,'Show the care log',logged['session_id']).json()
        assert log['ui_action']=='open_care_log'
        link=send(client,'Send me the photo link',logged['session_id']).json()
        assert link['ui_action']=='open_photo_link' and link['upload_url']
        fresh=send(client,'Start a new observation',logged['session_id']).json()
        assert fresh['session_id']!=logged['session_id'] and fresh['event_id'] is None
        assert get_event(logged['event_id']) is not None


def test_alexa_text_adapter_uses_same_language_correction_flow(isolated_db):
    from catnanny.alexa_skill.handlers import handle_conversation
    first=handle_conversation('Mochi vomited twice','voice-1')
    second=handle_conversation('Actually I meant Jeremy, not Mochi','voice-2',first['session_attributes'])
    assert second['data']['status']=='awaiting_confirmation'
    final=handle_conversation('Yes','voice-3',second['session_attributes'])
    assert final['data']['cat_name']=='Jeremy'
    assert final['data']['event_id']==first['data']['event_id']


def test_correction_does_not_silently_apply_to_an_unrelated_later_event(isolated_db):
    from app import app
    with TestClient(app) as client:
        original=seed(client)
        send(client,'I meant Jeremy',original['session_id'])
        fresh=send(client,'Start a new observation',original['session_id']).json()
        send(client,'Yes',fresh['session_id'])
        assert get_event(original['event_id']).cat_id=='mochi'
        assert not any(cat['name']=='Jeremy' for cat in cats())


def test_subject_answer_this_is_mochi_does_not_create_a_caregiver(isolated_db):
    from app import app
    with TestClient(app) as client:
        first=send(client,'My cat vomited.').json()
        resolved=send(client,'This is Mochi.',first['session_id']).json()
        assert resolved['cat_id']=='mochi' and resolved['event_type']=='vomit'
        assert all(person['name']!='Mochi' for person in client.get('/caregivers').json())


def test_chinese_unknown_subject_request_does_not_overwrite_current_cat(isolated_db):
    from app import app
    with TestClient(app) as client:
        original=seed(client)
        reply=send(client,'帮我记录一下Jeremy相关的信息',original['session_id']).json()
        assert reply['status']=='awaiting_cat'
        assert get_event(original['event_id']).cat_id=='mochi'
