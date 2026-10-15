import base64
from fastapi.testclient import TestClient
from catnanny.storage.repositories import get_event, list_event_photos

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aRZkAAAAASUVORK5CYII=')


def test_text_to_photo_to_report_complete_flow(isolated_db, monkeypatch):
    from app import app
    from catnanny.services import photo_service
    monkeypatch.setattr(photo_service, 'UPLOAD_DIR', isolated_db.DATA_DIR / 'uploads')
    with TestClient(app) as client:
        assert client.get('/').url.path == '/simulator'
        assert 'message-input' in client.get('/simulator').text
        for asset in ('app.css','chat.js','upload.js'):
            assert client.get('/assets/' + asset).status_code == 200
        first = client.post('/conversations/turns', json={'cat_id':'mochi','request_id':'ui1','text':'猫今天吐了两次'}).json()
        session = first['session_id']
        for index, text in enumerate(['食物','没有','精神正常']):
            response = client.post('/conversations/turns', json={'cat_id':'mochi','request_id':f'ui{index+2}', 'session_id':session,'text':text})
            assert response.status_code == 200
            assert response.json()['event_id'] == first['event_id']
        assert response.json()['status'] == 'completed'
        assert 'photo-input' in client.get(first['upload_url']).text
        upload = client.post('/photos/upload', data={'event_id':first['event_id']}, files={'photo':('my-photo.png',PNG,'image/png')})
        assert upload.status_code == 200
        photo = upload.json()['photo']
        assert photo['event_id'] == first['event_id']
        assert len(list_event_photos(first['event_id'])) == 1
        detail = client.get('/events/' + first['event_id']).json()
        assert detail['photos'][0]['url'] == photo['url']
        timeline = client.get('/reports/vet-summary').json()['timeline']
        assert timeline[0]['photos'] == [photo['url']]
        assert client.get('/conversations/' + session + '/messages').json()['total'] == 4
        with isolated_db.get_connection() as conn:
            assert conn.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 1
        assert get_event(first['event_id']).details['has_blood'] is False


def test_invalid_photos_rejected_without_attachment(isolated_db, monkeypatch):
    from app import app
    from catnanny.services import photo_service
    monkeypatch.setattr(photo_service,'UPLOAD_DIR',isolated_db.DATA_DIR/'uploads')
    with TestClient(app) as client:
        event = client.post('/conversations/turns',json={'cat_id':'mochi','request_id':'photo','text':'猫吐了'}).json()['event_id']
        for content in [b'',b'<svg onload="alert(1)"></svg>',b'not a picture']:
            response=client.post('/photos/upload',data={'event_id':event},files={'photo':('fake.png',content,'image/png')})
            assert response.status_code == 422
        monkeypatch.setattr(photo_service,'MAX_PHOTO_BYTES',10)
        assert client.post('/photos/upload',data={'event_id':event},files={'photo':('big.png',PNG,'image/png')}).status_code==422
        assert list_event_photos(event)==[]


def test_photo_binding_does_not_change_another_event(isolated_db, monkeypatch):
    from app import app
    from catnanny.services import photo_service
    monkeypatch.setattr(photo_service,'UPLOAD_DIR',isolated_db.DATA_DIR/'uploads')
    with TestClient(app) as client:
        a=client.post('/conversations/turns',json={'cat_id':'mochi','request_id':'a','text':'猫吐了'}).json()
        b=client.post('/conversations/turns',json={'cat_id':'mochi','request_id':'b','text':'猫不吃饭'}).json()
        assert client.post('/photos/upload',data={'event_id':a['event_id']},files={'photo':('photo.html',PNG,'image/png')}).status_code==200
        photos=list_event_photos(a['event_id'])
        assert photos[0].url.endswith('.png')
        assert list_event_photos(b['event_id'])==[]
        assert client.post('/photos/upload',data={'event_id':'missing'},files={'photo':('photo.png',PNG,'image/png')}).status_code==404
