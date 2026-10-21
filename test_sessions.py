"""Account isolation and browser camera lifecycle regression tests."""
import secrets
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import cv2
import numpy as np
import app as server
from leaderboard import LeaderboardStore
from sessions import SessionRegistry


def authorize_client(app,client,email=None):
    app.auth_attempts.clear()
    email=email or secrets.token_hex(5)+'@example.com'
    r=client.post('/auth/register',json={'email':email,'password':'Testing-pass-123','recovery_number':'48'})
    assert r.status_code==200,r.get_json()
    result=client.post('/session')
    assert result.status_code==200,result.get_json()
    token=result.json['session_token']
    client.environ_base['HTTP_X_COACH_SESSION']=token
    return token


class FakeDetector:
    def __init__(self):self.closed=False
    def detect_for_video(self,image,timestamp):
        return SimpleNamespace(pose_landmarks=[],pose_world_landmarks=[])
    def close(self):self.closed=True


class PrivateSessions(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=LeaderboardStore(Path(self.temp.name)/'test.db')
        self.registry=SessionRegistry(lambda:server.BrowserCoach(self.store))
        self.patches=[patch.object(server,'store',self.store),patch.object(server,'sessions',self.registry),
            patch.object(server.vision.PoseLandmarker,'create_from_options',side_effect=lambda *_:FakeDetector())]
        for p in self.patches:p.start()
        self.addCleanup(self.cleanup)
        self.a=server.app.test_client();self.b=server.app.test_client()
        self.ta=authorize_client(server,self.a,'alice@example.com')
        self.tb=authorize_client(server,self.b,'bob@example.com')
        self.pa=self.a.post('/profiles',json={'name':'Alice'}).json['profile']
        self.pb=self.b.post('/profiles',json={'name':'Bob'}).json['profile']

    def cleanup(self):
        self.registry.stop_all()
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def start(self,client,profile):
        r=client.post('/start',json={'profile_id':profile['id'],'exercise':'curl','arm':'right'})
        self.assertEqual(r.status_code,200,r.json)

    def frame(self,client,set_id):
        _,image=cv2.imencode('.jpg',np.zeros((240,320,3),dtype=np.uint8))
        return client.post('/frame',data=image.tobytes(),content_type='image/jpeg',headers={'X-Set-ID':set_id})

    def test_no_account_no_camera_or_profiles(self):
        client=server.app.test_client()
        for path in ('/start','/stop','/pause'):
            self.assertEqual(client.post(path).status_code,401)
        self.assertEqual(client.get('/profiles').status_code,401)
        self.assertNotIn('reps',client.get('/status').json)
        self.assertEqual(client.get('/video_feed').status_code,410)

    def test_two_cameras_private_counters_and_stop(self):
        self.start(self.a,self.pa);self.start(self.b,self.pb)
        ca=self.registry.items[self.ta]['coach'];cb=self.registry.items[self.tb]['coach']
        self.assertIsNot(ca.detector,cb.detector)
        ca.forms['right'].counter.reps=4;ca.outputs['right']=ca.forms['right'].base();ca.aggregate()
        cb.forms['right'].counter.reps=2;cb.outputs['right']=cb.forms['right'].base();cb.aggregate()
        self.assertEqual(self.a.get('/status').json['reps'],4)
        self.assertEqual(self.b.get('/status').json['reps'],2)
        self.a.post('/stop')
        self.assertFalse(ca.state['running']);self.assertTrue(cb.state['running'])
        self.assertEqual(self.b.get('/status').json['reps'],2)
        self.assertEqual(self.frame(self.b,cb.state['set_id']).status_code,200)
        self.b.post('/stop')
        rows=self.store.standings('curl','right')
        self.assertEqual([(r['name'],r['total']) for r in rows],[('Alice',4),('Bob',2)])

    def test_profile_health_and_calendar_ownership(self):
        self.assertEqual(self.a.get('/profiles').json['profiles'],[self.pa])
        self.assertEqual(self.b.get('/profiles').json['profiles'],[self.pb])
        for suffix in ('health','calendar'):
            self.assertEqual(self.b.get(f'/profiles/{self.pa["id"]}/{suffix}').status_code,404)
        self.assertEqual(self.b.post('/start',json={'profile_id':self.pa['id']}).status_code,404)
        self.assertEqual(self.b.post('/profiles',json={'name':'Alice'}).status_code,400)
        self.assertEqual(self.b.post(f'/profiles/{self.pa["id"]}/calendar/day',json={}).status_code,404)
        self.assertEqual(self.b.post(f'/profiles/{self.pa["id"]}/health',json={}).status_code,404)

    def test_stolen_session_header_requires_matching_login_cookie(self):
        self.assertEqual(self.b.get('/status',headers={'X-Coach-Session':self.ta}).status_code,401)
        self.assertEqual(self.b.post('/stop',headers={'X-Coach-Session':self.ta}).status_code,401)

    def test_password_hashed_login_and_restart(self):
        with self.store.connect() as db:
            hashed=db.execute('SELECT password_hash FROM accounts WHERE email=?',('alice@example.com',)).fetchone()[0]
        self.assertNotEqual(hashed,'Testing-pass-123');self.assertTrue(hashed.startswith('scrypt:'))
        c=server.app.test_client()
        self.assertEqual(c.post('/auth/login',json={'email':'Alice@example.com','password':'wrong-pass'}).status_code,400)
        self.assertEqual(c.post('/auth/login',json={'email':'ALICE@example.com','password':'Testing-pass-123'}).status_code,200)
        token=c.post('/session').json['session_token']
        self.assertEqual(c.get('/profiles',headers={'X-Coach-Session':token}).json['profiles'],[self.pa])
        self.assertEqual(c.get('/auth/me').json['email'],'alice@example.com')

    def test_same_account_tabs_are_independent_but_same_profile_has_one_writer(self):
        second=self.a.post('/session').json['session_token']
        self.start(self.a,self.pa)
        self.assertFalse(self.a.get('/status',headers={'X-Coach-Session':second}).json['running'])
        self.assertEqual(self.a.post('/start',json={'profile_id':self.pa['id']},headers={'X-Coach-Session':second}).status_code,409)
        self.a.post('/stop',headers={'X-Coach-Session':second})
        self.assertTrue(self.a.get('/status').json['running'])

    def test_logout_revokes_cookie_and_saves_only_own_camera(self):
        self.start(self.a,self.pa);self.start(self.b,self.pb)
        self.assertEqual(self.a.post('/auth/logout').status_code,200)
        self.assertEqual(self.a.get('/status').status_code,401)
        self.assertFalse(self.registry.items[self.ta]['coach'].state['running'])
        self.assertTrue(self.b.get('/status').json['running'])

    def test_frame_validation_and_stale_set_cannot_count(self):
        self.start(self.a,self.pa)
        current=self.a.get('/status').json['set_id']
        self.assertEqual(self.frame(self.a,'old-set').status_code,409)
        self.assertEqual(self.frame(self.a,current).status_code,200)
        self.assertEqual(self.a.post('/frame',data=b'bad',content_type='image/jpeg').status_code,400)
        self.assertEqual(self.a.post('/frame',json={}).status_code,415)
        self.a.post('/stop')
        self.assertEqual(self.frame(self.a,current).status_code,409)

    def test_disconnected_browser_auto_stop(self):
        self.start(self.a,self.pa);self.start(self.b,self.pb)
        a=self.registry.items[self.ta]['coach'];a.last_frame_at=time.monotonic()-21
        self.registry.sweep()
        self.assertFalse(a.state['running']);self.assertTrue(self.b.get('/status').json['running'])

    def test_csrf_and_login_rate_limit(self):
        self.assertEqual(self.a.post('/auth/logout',headers={'Origin':'https://evil.example'}).status_code,403)
        server.auth_attempts.clear()
        with patch.object(server.accounts,'login',side_effect=ValueError('bad')):
            for _ in range(15):self.a.post('/auth/login',json={})
            self.assertEqual(self.a.post('/auth/login',json={}).status_code,429)
        server.auth_attempts.clear()

    def test_legacy_migration_only_local_first_account(self):
        old=self.store.create_profile('Before V7')
        server.PUBLIC_URL='https://demo.trycloudflare.com'
        self.addCleanup(setattr,server,'PUBLIC_URL',None)
        # A remote visitor cannot adopt unowned old profiles, even knowing a name.
        c=server.app.test_client();base='http://45-public.invalid'
        c.get('/45-fitness-coach?key='+server.ACCESS_KEY,base_url=base)
        server.auth_attempts.clear()
        self.assertEqual(c.post('/auth/register',json={'email':'remote@example.com','password':'Testing-pass-123','recovery_number':'48'},base_url=base).status_code,200)
        r=c.post('/session',base_url=base);self.assertEqual(r.status_code,200)
        token=r.json['session_token']
        self.assertEqual(c.get('/profiles',base_url=base,headers={'X-Coach-Session':token}).json['profiles'],[])
        local=self.a.post('/session').json['session_token']
        profiles=self.a.get('/profiles',headers={'X-Coach-Session':local}).json['profiles']
        self.assertIn(old,profiles)


if __name__=='__main__':unittest.main()
