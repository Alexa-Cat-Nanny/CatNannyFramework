import base64
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from catnanny.domain.models import Event, EventType
from catnanny.storage.repositories import save_event


def test_missing_subject_asks_before_event_is_saved_and_preserves_observation(isolated_db):
    from app import app
    with TestClient(app) as client:
        first=client.post('/conversations/turns',json={'request_id':'unknown','text':'My cat vomited twice today.'}).json()
        assert first['status']=='awaiting_cat'
        assert first['cat_id'] is None and first['event_id'] is None
        assert first['missing_fields']==['cat_id']
        with isolated_db.get_connection() as conn:
            assert conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]==0
        second=client.post('/conversations/turns',json={'request_id':'name','session_id':first['session_id'],'text':'Mochi'}).json()
        assert second['cat_id']=='mochi'
        assert second['event_type']=='vomit'
        assert second['details']['episode_count']==2
        assert second['follow_up']=='Was it food, a hairball, liquid, or foam?'


def test_named_cat_switch_keeps_records_separate(isolated_db,monkeypatch):
    from app import app
    from catnanny.services import photo_service
    monkeypatch.setattr(photo_service,'UPLOAD_DIR',isolated_db.DATA_DIR/'uploads')
    with TestClient(app) as client:
        jeremy=client.post('/cats',json={'name':'Jeremy','sex':'male'}).json()
        first=client.post('/conversations/turns',json={'request_id':'mochi','text':'Mochi vomited twice.'}).json()
        second=client.post('/conversations/turns',json={'request_id':'jeremy','session_id':first['session_id'],'cat_id':'mochi','text':'Jeremy is not eating.'}).json()
        assert second['cat_id']==jeremy['cat_id']
        assert second['session_id']!=first['session_id']
        assert second['event_id']!=first['event_id']
        assert client.get('/events',params={'cat_id':'mochi'}).json()['total']==1
        assert client.get('/events',params={'cat_id':jeremy['cat_id']}).json()['total']==1
        assert client.get('/conversations/'+first['session_id'],params={'cat_id':jeremy['cat_id']}).status_code==404
        assert client.get('/conversations/'+first['session_id']+'/messages',params={'cat_id':jeremy['cat_id']}).status_code==404
        png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aRZkAAAAASUVORK5CYII=')
        assert client.post('/photos/upload',data={'event_id':second['event_id']},files={'photo':('photo.png',png,'image/png')}).status_code==200
        assert client.get('/events/'+first['event_id']).json()['photos']==[]
        report=client.get('/reports/vet-summary',params={'cat_id':jeremy['cat_id']}).json()
        assert report['cat']=='Jeremy'
        assert len(report['timeline'])==1 and len(report['timeline'][0]['photos'])==1


def test_two_named_cats_need_clarification(isolated_db):
    from app import app
    with TestClient(app) as client:
        client.post('/cats',json={'name':'Jeremy'})
        result=client.post('/conversations/turns',json={'request_id':'both','text':'Mochi and Jeremy are not eating.'}).json()
        assert result['status']=='awaiting_cat'
        assert result['event_id'] is None


def test_caregiver_attribution_each_turn_and_seven_day_default(isolated_db):
    from app import app
    with TestClient(app) as client:
        person=client.post('/caregivers',json={'name':'Sam'}).json()
        first=client.post('/conversations/turns',json={'request_id':'sam','text':'Mochi vomited food.','caregiver_id':person['caregiver_id']}).json()
        second=client.post('/conversations/turns',json={'request_id':'alex','session_id':first['session_id'],'text':'No','caregiver_id':'demo_caregiver'}).json()
        assert first['caregiver_name']=='Sam' and second['caregiver_name']=='Alex'
        detail=client.get('/events/'+first['event_id']).json()
        assert detail['reporter']=='Sam'
        save_event(Event(household_id='demo_household',cat_id='mochi',ts=datetime.now(timezone.utc)-timedelta(days=8),type=EventType.VOMIT))
        report=client.get('/reports/vet-summary').json()
        assert report['counts']['total_events']==1
        assert datetime.fromisoformat(report['end'])-datetime.fromisoformat(report['start'])==timedelta(days=7)
        assert client.get('/events').json()['total']==2


def test_profile_validation_and_english_defaults(isolated_db):
    from app import app
    with TestClient(app) as client:
        assert client.get('/cats').json()[0]['name']=='Mochi'
        assert client.post('/cats',json={'name':' mochi '}).status_code==409
        assert client.post('/cats',json={'name':'   '}).status_code==422
        assert client.get('/events',params={'cat_id':'missing'}).status_code==404
        assert client.get('/reports/vet-summary',params={'cat_id':'missing'}).status_code==404
        html=client.get('/simulator').text
        assert 'lang="en"' in html
        assert 'Add a companion' in html and 'Last 7 days' in html
        config=client.get('/capabilities').json()
        assert config['default_language']=='en' and config['default_report_days']==7


def test_unregistered_name_is_not_saved_to_current_cat(isolated_db):
    from app import app
    with TestClient(app) as client:
        first=client.post('/conversations/turns',json={'request_id':'m','text':'Mochi vomited.'}).json()
        pending=client.post('/conversations/turns',json={'request_id':'u','session_id':first['session_id'],'text':'Jeremy is not eating.'}).json()
        assert pending['status']=='awaiting_cat'
        assert client.get('/events?cat_id=mochi').json()['total']==1
        jeremy=client.post('/cats',json={'name':'Jeremy'}).json()
        resolved=client.post('/conversations/turns',json={'request_id':'j','session_id':first['session_id'],'text':'Jeremy'}).json()
        assert resolved['cat_id']==jeremy['cat_id']
        assert resolved['details']['status']=='not_eating'
        assert client.get('/events?cat_id=mochi').json()['total']==1
