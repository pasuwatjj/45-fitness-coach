"""Push-up counting, reset email security, consent and camera lifecycle regressions."""
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import app as server
import accounts, recovery, password_mail
from cardio import PushUpRound,history
import test_v13 as fixtures

class Features(unittest.TestCase):
    setUp=fixtures.RouteTests.setUp
    def test_favorite_number_limits(self):
        for n in ('00','12','123'):self.assertEqual(recovery.number(n),n)
        for n in ('1','1234','1a',12,' 12'):
            with self.assertRaises(ValueError):recovery.number(n)
    def test_email_reset_single_use_revokes_sessions(self):
        email=self.a.get('/auth/me').json['email']
        with patch.object(password_mail,'deliver') as send:
            password_mail.issue_and_send(self.store,email,'https://fitness.example/45-fitness-coach')
        self.assertEqual(send.call_args.args[0],email)
        ticket=send.call_args.args[1].split('#reset=')[1]
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM recovery_tickets WHERE token_hash=?',(ticket,)).fetchone())
        body={'ticket':ticket,'password':'Changed-pass-123'}
        self.assertEqual(self.a.post('/auth/recovery/reset',json=body).status_code,200)
        self.assertEqual(self.a.get('/profiles').status_code,401)
        self.assertEqual(self.a.post('/auth/recovery/reset',json=body).status_code,400)
        self.assertEqual(self.a.post('/auth/login',json={'email':email,'password':'Testing-pass-123'}).status_code,400)
        self.assertEqual(self.a.post('/auth/login',json={'email':email,'password':'Changed-pass-123'}).status_code,200)
    def test_expiry_and_email_failure(self):
        email=self.a.get('/auth/me').json['email']
        with patch.object(password_mail,'deliver') as send:password_mail.issue_and_send(self.store,email,'https://fitness.example')
        token=send.call_args.args[1].split('#reset=')[1]
        with patch.object(recovery.time,'time',return_value=time.time()+901),self.assertRaises(ValueError):recovery.reset(self.store,token,'Changed-pass-123')
        with patch.object(password_mail,'deliver',side_effect=RuntimeError('mail')),self.assertLogs(level='WARNING'):password_mail.issue_and_send(self.store,email,'https://fitness.example')
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM recovery_tickets').fetchone()[0],1)
    def test_request_never_exposes_account_or_ticket_and_rate_limits(self):
        email=self.a.get('/auth/me').json['email']
        with patch.object(password_mail,'smtp_ready',return_value=True),patch.object(server,'public_share_url',return_value='https://fitness.example/45-fitness-coach'),patch.object(password_mail._pool,'submit') as submit:
            # Complete mocked work immediately so bounded slots are released.
            from concurrent.futures import Future
            f=Future();f.set_result(None);submit.return_value=f
            first=self.a.post('/auth/recovery/verify',json={'email':email})
            missing=self.a.post('/auth/recovery/verify',json={'email':'missing@example.com'})
            self.assertEqual(first.json,missing.json);self.assertNotIn('ticket',first.json)
            for _ in range(3):self.a.post('/auth/recovery/verify',json={'email':email})
            self.assertEqual(self.a.post('/auth/recovery/verify',json={'email':email}).status_code,400)
    def test_no_mail_configuration_does_not_claim_sent(self):
        with patch.object(password_mail,'smtp_ready',return_value=False):
            self.assertEqual(self.a.post('/auth/recovery/verify',json={'email':'user@example.com'}).status_code,400)
    def test_shared_profile_consent_and_revocation(self):
        for view in ('overview','progress','angles'):self.assertEqual(self.b.get(f'/social/profiles/{self.pa}/{view}').status_code,403)
        self.assertEqual(self.b.post(f'/social/sharing/{self.pa}',json={'enabled':True}).status_code,404)
        self.assertEqual(self.a.post(f'/social/sharing/{self.pa}',json={'enabled':True}).status_code,200)
        for view in ('overview','progress','angles'):
            r=self.b.get(f'/social/profiles/{self.pa}/{view}')
            self.assertEqual(r.status_code,200);self.assertEqual(r.json,self.a.get(f'/profiles/{self.pa}/{view}').json)
            self.assertIn('no-store',r.headers['Cache-Control'])
        self.assertEqual(self.b.get(f'/profiles/{self.pa}/overview').status_code,404)
        self.a.post(f'/social/sharing/{self.pa}',json={'enabled':False})
        self.assertEqual(self.b.get(f'/social/profiles/{self.pa}/overview').status_code,403)
    def test_incoming_friend_request_then_accept(self):
        other=int(self.reg.items[self.tb]['owner'].split(':')[1]);own=int(self.owner.split(':')[1])
        self.assertEqual(self.a.post('/social/friends',json={'account_id':other,'action':'request'}).status_code,200)
        inbox=self.b.get('/social/friends').json['requests'];self.assertTrue(inbox[0]['incoming']);self.assertEqual(inbox[0]['status'],'pending')
        self.assertEqual(self.b.post('/social/friends',json={'account_id':own,'action':'accept'}).status_code,200)
        self.assertEqual(self.a.get('/social/friends').json['requests'][0]['status'],'accepted')
    def test_pushup_and_jacks_200_camera_cycles_two_users(self):
        for i in range(200):
            for client,pid in ((self.a,self.pa),(self.b,self.pb)):
                r=client.post('/cardio/start',json={'profile_id':pid,'mode':['pushup','full','upper'][i%3]})
                self.assertEqual(r.status_code,200,r.json)
            self.a.post('/stop');self.assertTrue(self.reg.items[self.tb]['coach'].state['running']);self.b.post('/stop')
        self.assertFalse(any(x['coach'].state['running'] for x in self.reg.items.values()))
    def test_pushup_cycles_visibility_wrong_pose_and_rewards(self):
        now=[0.];r=PushUpRound(self.store,self.pa,'pushup',clock=lambda:now[0])
        def points(down=False):
            ps=[SimpleNamespace(x=0.,y=0.,visibility=0.) for _ in range(33)]
            for i,(x,y) in {11:(.2,.5),13:((.35,.5) if down else (.2,.65)),15:((.35,.65) if down else (.2,.8)),23:(.5,.5),25:(.65,.5),27:(.8,.5)}.items():ps[i]=SimpleNamespace(x=x,y=y,visibility=1.)
            return ps
        def hold(ps):
            r.update(ps);now[0]+=.08;return r.update(ps)
        hold(points());self.assertIsNotNone(r.start_at);now[0]=r.start_at+.1;hold(points())
        hold(points(True));hold(points());self.assertEqual(r.reps,1)
        for _ in range(5):hold(points())
        self.assertEqual(r.reps,1)
        hold(points(True));r.update(None);hold(points());self.assertEqual(r.reps,1)
        bad=points(True);bad[23].y=.75;hold(bad);hold(points());self.assertEqual(r.reps,1)
        upright=points();upright[27].x=.21;upright[27].y=.95;hold(upright);self.assertEqual(r.cue,'push_side')
        hold(points());hold(points(True));hold(points());self.assertEqual(r.reps,2)
        now[0]=r.start_at+16;r.snapshot();r.snapshot()
        rows=history(self.store,self.pa);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['reps'],2);self.assertIsNone(rows[0]['kcal'])
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT SUM(amount) FROM reward_ledger WHERE profile_id=?',(self.pa,)).fetchone()[0],2)

if __name__=='__main__':unittest.main()
