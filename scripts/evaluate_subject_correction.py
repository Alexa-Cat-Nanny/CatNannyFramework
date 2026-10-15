"""One opt-in live action-classification test, isolated from real household data."""
import argparse
import base64
import json
import os
import sys
from io import BytesIO
from pathlib import Path
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--env-file',default='.env')
    args=parser.parse_args()
    if not args.live:parser.error('Pass --live to authorize a small real API call.')
    from dotenv import load_dotenv
    load_dotenv(args.env_file)
    root=Path(__file__).resolve().parents[1]
    run=root/'data'/'evaluations'/f'subject-correction-{uuid4().hex}'
    run.mkdir(parents=True)
    os.environ['CATNANNY_DATA_DIR']=str(run)
    os.environ['CATNANNY_EXTRACTION_PROVIDER']='openai'
    from catnanny.storage.database import init_db,get_connection
    from catnanny.domain.schemas import ConversationRequest
    from catnanny.domain.extraction import ExtractionError
    from catnanny.services.conversation_service import process_turn
    from catnanny.services.report_service import build_vet_summary
    from catnanny.services import photo_service
    from catnanny.storage.repositories import get_event,list_event_photos
    from fastapi import UploadFile
    init_db()
    photo_service.UPLOAD_DIR=run/'uploads'
    original=process_turn(ConversationRequest(request_id='original',cat_id='mochi',event_type='vomit',
        details={'content':'food','has_blood':False,'episode_count':2,'low_energy':False}))
    png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aRZkAAAAASUVORK5CYII=')
    photo_service.save_event_photo(original['event_id'],UploadFile(filename='sample.png',file=BytesIO(png)))
    try:
        proposed=process_turn(ConversationRequest(request_id='indirect-correction',session_id=original['session_id'],
            text='I misspoke; the cat I was referring to was Jeremy, not Mochi.'))
        assert proposed['status']=='awaiting_confirmation','Expected confirmation before creating Jeremy'
        assert get_event(original['event_id']).cat_id=='mochi','Moved before confirmation'
        corrected=process_turn(ConversationRequest(request_id='confirmation',session_id=original['session_id'],text='Yes'))
        assert corrected['cat_name']=='Jeremy' and corrected['event_id']==original['event_id']
        assert corrected['details']==original['details']
        assert list_event_photos(original['event_id'])[0].cat_id==corrected['cat_id']
        assert build_vet_summary(cat_id='mochi')['counts']['total_events']==0
        assert build_vet_summary(cat_id=corrected['cat_id'])['counts']['total_events']==1
        with get_connection() as conn:
            assert conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]==1
            assert conn.execute('SELECT COUNT(*) FROM event_reassignments').fetchone()[0]==1
        result={'passed':True,'tested':'Indirect natural-language correction, unknown profile confirmation, same event and photo reassignment'}
    except ExtractionError as error:
        result={'passed':False,'error_code':error.code}
    except AssertionError as error:
        result={'passed':False,'reason':str(error)}
    (run/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Subject correction:', 'PASS' if result['passed'] else 'FAIL')
    print('Isolated results:',run/'result.json')
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
