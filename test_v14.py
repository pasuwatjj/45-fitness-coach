"""Guest ownership, recovery, manual VIP review and relaxed directional counting."""
import math
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch
from pathlib import Path
import app as server
import recovery
import membership
import accounts
import visitors
import cv2
import numpy as np
import test_v13 as fixtures
from test_v13 import picture
from test_v11 import landmarks
from strict_form import geometry

class GuestTests(unittest.TestCase):
    setUp=fixtures.RouteTests.setUp
    def test_guest_can_train_and_reopen_without_creating_name(self):
        c=server.app.test_client();a=c.post('/session').json
        p=a['default_profile'];self.assertTrue(a['guest'])
        c.environ_base['HTTP_X_COACH_SESSION']=a['session_token']
        self.assertEqual(c.post('/start',json=dict(profile_id=p['id'],exercise='curl',arm='right')).status_code,200)
        self.assertEqual(c.post('/stop').status_code,200)
        b=c.post('/session').json
        self.assertEqual(b['default_profile'],p);self.assertNotEqual(a['session_token'],b['session_token'])
    def test_guests_isolated_and_cannot_buy_vip_anonymously(self):
        c=server.app.test_client();d=server.app.test_client()
        a=c.post('/session').json;b=d.post('/session').json
        c.environ_base['HTTP_X_COACH_SESSION']=a['session_token'];d.environ_base['HTTP_X_COACH_SESSION']=b['session_token']
        self.assertEqual(d.get('/profiles/'+str(a['default_profile']['id'])+'/overview').status_code,404)
        self.assertTrue(c.get('/vip').json['account_required'])
        self.assertEqual(c.post('/vip/slips',data=picture(),content_type='image/png').status_code,403)
        self.assertEqual(c.post('/start',json=dict(profile_id=a['default_profile']['id'],exercise='front_raise',arm='right')).status_code,403)
    def test_signup_preserves_own_guest_profile_and_revokes_old_session(self):
        c=server.app.test_client();a=c.post('/session').json
        c.environ_base['HTTP_X_COACH_SESSION']=a['session_token']
        r=c.post('/auth/register',json=dict(email='new@example.com',password='Password-test-456',recovery_number='583'))
        self.assertEqual(r.status_code,200)
        self.assertEqual(c.get('/profiles').status_code,401)
        b=c.post('/session',json={'auto_profile':True}).json
        self.assertEqual(b['default_profile'],a['default_profile'])
        self.assertFalse(b['guest'])
    def test_account_reuses_existing_profile(self):
        a=self.a.post('/session',json={'auto_profile':True}).json
        b=self.a.post('/session',json={'auto_profile':True}).json
        self.assertEqual(a['default_profile']['id'],self.pa)
        self.assertEqual(a['default_profile'],b['default_profile'])
    def test_transient_frame_error_and_old_error_do_not_stop_new_camera(self):
        self.a.post('/start',json=dict(profile_id=self.pa,exercise='curl',arm='right'))
        coach=self.reg.items[self.ta]['coach'];set_id=coach.state['set_id']
        _,image=cv2.imencode('.jpg',np.zeros((240,320,3),dtype=np.uint8))
        def send():return self.a.post('/frame',data=image.tobytes(),content_type='image/jpeg',headers={'X-Set-ID':set_id,'X-Frame-Format':'landmarks'})
        with patch.object(coach,'accept_frame',side_effect=RuntimeError('temporary')),self.assertLogs(level='ERROR'):
            self.assertEqual(send().status_code,503)
        self.assertTrue(coach.state['running'])
        def stale(*args):
            coach.new_set()
            raise RuntimeError('old frame')
        with patch.object(coach,'accept_frame',side_effect=stale),self.assertLogs(level='ERROR'):
            self.assertEqual(send().status_code,409)
        self.assertTrue(coach.state['running']);self.assertNotEqual(coach.state['set_id'],set_id)
    def test_hand_tracker_failure_preserves_body_camera(self):
        self.a.post('/start',json=dict(profile_id=self.pa,exercise='curl',arm='right'))
        coach=self.reg.items[self.ta]['coach']
        _,image=cv2.imencode('.jpg',np.zeros((240,320,3),dtype=np.uint8))
        # The default FakeDetector is empty; hand tracking requires a visible body.
        coach.detector.detect_for_video=lambda *_:SimpleNamespace(pose_landmarks=[landmarks()[0]],pose_world_landmarks=[landmarks()[1]])
        with patch.object(server.mp.solutions.hands,'Hands',side_effect=RuntimeError('hand tracker unavailable')),self.assertLogs(level='ERROR'):
            result=self.a.post('/frame',data=image.tobytes(),content_type='image/jpeg',headers={'X-Set-ID':coach.state['set_id'],'X-Frame-Format':'landmarks'})
        self.assertEqual(result.status_code,200);self.assertEqual(result.json['hands'],[]);self.assertTrue(result.json['state']['running'])
    def test_manual_slip_pending_and_duplicate_never_activates(self):
        with patch.object(membership,'payment_ready',return_value=False):
            for _ in range(2):
                d=self.a.post('/vip/slips',data=picture(),content_type='image/png').json
                self.assertFalse(d['active']);self.assertEqual(d['receipts'][0]['status'],'review')
        self.assertEqual(len(d['receipts']),1)
        rid=d['receipts'][0]['id']
        with self.assertRaises(ValueError):membership.approve_manual(self.store,rid,'004:ACTUAL0001',49,'1191841480')
        membership.approve_manual(self.store,rid,'004:ACTUAL0001',50,'1191841480')
        expires=membership.status(self.store,self.owner)['expires']
        membership.approve_manual(self.store,rid,'004:ACTUAL0001',50,'1191841480')
        self.assertEqual(expires,membership.status(self.store,self.owner)['expires'])
        other=membership.submit_manual(self.store,'account:999','other@example.com',picture('blue'))['receipts'][0]['id']
        with self.assertRaises(ValueError):membership.approve_manual(self.store,other,'004:ACTUAL0001',50,'1191841480')
    def test_short_number_cannot_reset_password(self):
        email=self.a.get('/auth/me').json['email']
        with self.assertRaises(ValueError):recovery.verify(self.store,email,'48','network')
    def test_existing_account_can_set_favorite_only_with_password(self):
        self.assertEqual(self.a.post('/auth/recovery/setup',json=dict(password='wrong-pass',recovery_number='928')).status_code,400)
        self.assertEqual(self.a.post('/auth/recovery/setup',json=dict(password='Testing-pass-123',recovery_number='928')).status_code,200)
        with self.store.connect() as db:
            data=db.execute('SELECT number_hash FROM recovery_numbers LIMIT 1').fetchone()[0]
        from werkzeug.security import check_password_hash
        self.assertTrue(check_password_hash(data,'928'))
    def test_small_arm_drift_counts_but_sideways_and_backward_reject(self):
        p,w=landmarks(80);e=w[14];v=(w[16].x-e.x,w[16].y-e.y,w[16].z-e.z)
        a=math.radians(25);e.y=.3*math.cos(a);e.z=-.3*math.sin(a)
        w[16].x=e.x+v[0];w[16].y=e.y+v[1];w[16].z=e.z+v[2]
        self.assertNotIn('upper_position',geometry('curl','right',p,w,{})[1])
        for plane in ('side','back'):
            p,w=landmarks(80,path=plane)
            self.assertIn('curl_path',geometry('curl','right',p,w,{})[1])
    def test_jeff_images_and_all_steps_packaged(self):
        for ex in server.EXERCISES:
            if ex['id'] in ('lying_triceps','supported_row'):self.assertNotIn('image_credit',ex)
            else:self.assertEqual(ex['image_credit'],'Jeff')
            for image in ex['images']:self.assertTrue((Path(__file__).parent/image.lstrip('/')).exists())
        self.assertEqual(len(server.CATALOG['front_raise']['images']),3)

if __name__=='__main__':unittest.main()
