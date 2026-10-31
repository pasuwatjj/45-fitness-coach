"""Deployment and slow-network regressions; no physical-camera accuracy claim."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
import app as server
from leaderboard import LeaderboardStore
from test_v11 import landmarks


class SlowCameraTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = LeaderboardStore(Path(self.temp.name)/'fitness.db')
        self.coach = server.BrowserCoach(self.store)
        self.coach.grip_enabled = False
        self.image = np.zeros((480,640,3),dtype=np.uint8)
        self.angle = 160
        def detect(*args):
            p,w = landmarks(self.angle)
            return SimpleNamespace(pose_landmarks=[p],pose_world_landmarks=[w])
        self.detector = SimpleNamespace(detect_for_video=detect,close=lambda:None)
        with patch('app.vision.PoseLandmarker.create_from_options',return_value=self.detector):
            self.coach.start('right',0,10)
        self.coach.last_frame_at=100
        self.addCleanup(self.coach.stop)

    def frame(self, now):
        with patch('app.time.monotonic',return_value=now):
            return self.coach.accept_frame(self.image,self.coach.state['set_id'],True)['state']

    def test_slow_network_reference_is_immediate_without_free_reps(self):
        self.assertTrue(self.frame(102.2)['calibrated'])
        self.assertTrue(self.frame(104.4)['calibrated'])
        self.assertTrue(self.frame(106.6)['calibrated'])
        self.assertEqual(self.frame(108.8)['reps'],0)

    def test_missing_frames_cancel_rep_but_keep_short_gap_calibration(self):
        for now in (100.1,101.2,102.3):self.frame(now)
        self.assertIsNotNone(self.coach.forms['right'].baseline)
        self.coach.forms['right'].counter.phase='raised'
        result=self.frame(105)
        self.assertTrue(result['calibrated'])
        self.assertEqual(result['reps'],0)
        self.assertNotEqual(self.coach.forms['right'].counter.phase,'raised')
        self.assertFalse(self.frame(116)['calibrated'])

    def test_jitter_reference_does_not_grant_free_reps(self):
        from form_rules import FormCoach
        for lean,arm,expected in [(0,0,True),(35,0,True),(0,40,True)]:
            f=FormCoach(server.SETTINGS)
            for i in range(9):
                out=f.update(dict(elbow=160,lean=lean+(i%2)*8,arm=arm+(i%2)*10),i*300)
            self.assertEqual(out['calibrated'],expected)
            self.assertEqual(out['reps'],0)


class AccountRestartTests(unittest.TestCase):
    def test_account_cookie_profile_and_duplicate_survive_real_process_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            env=dict(os.environ,FITNESS_DATA_PATH=str(Path(temp)/'fitness.db'))
            common="""
import app as s
s.auth_attempts.clear()
c=s.app.test_client()
"""
            first=common+"""
r=c.post('/auth/register',json=dict(email=' Restart@Example.com ',password='Example-test-123',recovery_number='48'))
assert r.status_code==200,r.json
session=c.post('/session',json={'auto_profile':True}).json
print('RESULT:'+__import__('json').dumps({'cookie':c.get_cookie(s.accounts.COOKIE).value,'profile':session['default_profile']['id']}))
"""
            run=subprocess.run([sys.executable,'-c',first],env=env,text=True,capture_output=True,check=True)
            saved=json.loads(next(x[7:] for x in run.stdout.splitlines() if x.startswith('RESULT:')))
            env['RESTART_TEST_LOGIN']=saved['cookie'];env['RESTART_TEST_PROFILE']=str(saved['profile'])
            second=common+"""
import os
c.set_cookie(s.accounts.COOKIE,os.environ['RESTART_TEST_LOGIN'])
assert c.get('/auth/me').json['email']=='restart@example.com'
r=c.post('/session',json={'auto_profile':True})
assert r.json['guest'] is False
assert r.json['default_profile']['id']==int(os.environ['RESTART_TEST_PROFILE'])
for email in ['restart@example.com',' RESTART@EXAMPLE.COM ']:
 r=c.post('/auth/register',json=dict(email=email,password='Example-test-123',recovery_number='48'))
 assert r.status_code==400,r.json
with s.store.connect() as db:assert db.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]==1
c.post('/auth/logout')
assert c.get('/auth/me').json['guest'] is True
assert c.post('/auth/login',json=dict(email='RESTART@example.com',password='Example-test-123')).status_code==200
"""
            subprocess.run([sys.executable,'-c',second],env=env,text=True,capture_output=True,check=True)

if __name__=='__main__':unittest.main()
