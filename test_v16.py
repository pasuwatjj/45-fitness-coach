"""Regression coverage for camera renewal, roles, VIP review and friend privacy."""
import time,uuid
import unittest
from unittest.mock import patch
import app as server
import community,membership
import test_v13 as fixtures

class V16Tests(unittest.TestCase):
    setUp=fixtures.RouteTests.setUp
    def admin(self):
        community.grant_admin(self.store,self.a.get('/auth/me').json['email'])
    def uid(self,client):return client.get('/social/me').json['account_id']
    def test_admin_is_required_for_every_admin_endpoint(self):
        uid=self.uid(self.b)
        paths=['/admin/accounts','/admin/receipts',f'/admin/profiles/{self.pa}','/admin/receipts/missing/image']
        for path in paths:self.assertEqual(self.b.get(path).status_code,403,path)
        self.assertEqual(self.b.post(f'/admin/accounts/{uid}/vip',json={'days':30,'operation_id':str(uuid.uuid4())}).status_code,403)
        self.assertEqual(self.b.post('/admin/receipts/missing/approve',json={}).status_code,403)
        self.admin();self.assertEqual(self.a.get('/admin/accounts').status_code,200)
        self.assertEqual(self.a.get(f'/admin/profiles/{self.pb}').status_code,200)
    def test_vip_grant_idempotent_and_visible_in_public_badge(self):
        self.admin();uid=self.uid(self.b);body={'days':30,'operation_id':str(uuid.uuid4())}
        r=self.a.post(f'/admin/accounts/{uid}/vip',json=body);self.assertEqual(r.status_code,200)
        expiry=r.json['membership']['expires']
        self.assertEqual(self.a.post(f'/admin/accounts/{uid}/vip',json=body).json['membership']['expires'],expiry)
        self.assertTrue(self.b.get('/vip').json['active']);self.assertTrue(self.a.get(f'/social/players/{uid}').json['vip'])
        self.assertEqual(self.b.post('/start',json=dict(profile_id=self.pb,exercise='front_raise',arm='right')).status_code,200)
    def test_manual_receipt_admin_review_activates_only_once(self):
        self.admin()
        with patch.object(membership,'payment_ready',return_value=False):r=self.b.post('/vip/slips',data=fixtures.picture(),content_type='image/png')
        rid=r.json['receipts'][0]['id'];self.assertFalse(r.json['active'])
        data=dict(transaction='004:REALBANK0001',amount=50,receiver='0000000000',confirmed_bank_transfer=True)
        self.assertEqual(self.b.get(f'/admin/receipts/{rid}/image').status_code,403)
        self.assertEqual(self.a.get(f'/admin/receipts/{rid}/image').status_code,200)
        self.assertEqual(self.a.post(f'/admin/receipts/{rid}/approve',json={**data,'confirmed_bank_transfer':False}).status_code,400)
        self.assertEqual(self.a.post(f'/admin/receipts/{rid}/approve',json=data).status_code,200)
        expires=self.b.get('/vip').json['expires']
        self.a.post(f'/admin/receipts/{rid}/approve',json=data)
        self.assertEqual(self.b.get('/vip').json['expires'],expires)
    def test_friend_acceptance_and_private_fields(self):
        a,b=self.uid(self.a),self.uid(self.b)
        self.assertEqual(self.a.post('/social/friends',json={'account_id':b,'action':'request'}).status_code,200)
        self.assertEqual(self.a.post('/social/friends',json={'account_id':b,'action':'accept'}).status_code,409)
        self.assertEqual(self.b.post('/social/friends',json={'account_id':a,'action':'accept'}).status_code,200)
        self.assertEqual(self.a.get('/social/friends').json['requests'][0]['status'],'accepted')
        for path in ['/social/players',f'/social/players/{b}','/social/friends']:
            body=self.a.get(path).get_data(as_text=True)
            for secret in ['email','health','password','receipts']:self.assertNotIn('"'+secret+'"',body)
        self.assertEqual(self.a.get(f'/profiles/{self.pb}/overview').status_code,404)
    def test_camera_reset_reuses_coach_and_rejects_old_stop(self):
        other=self.reg.items[self.tb]['coach'];original=self.reg.items[self.ta]['coach']
        body=dict(profile_id=self.pa,exercise='curl',arm='right')
        for _ in range(5):
            state=self.a.get('/status').json
            r=self.a.post('/camera/recover',headers={'X-Set-ID':state['set_id']});self.assertEqual(r.status_code,200)
            fresh=self.reg.items[self.ta]['coach'];self.assertIs(original,fresh)
            self.assertEqual(self.a.post('/start',json=body).status_code,200)
            self.assertEqual(self.a.post('/stop',headers={'X-Set-ID':state['set_id']}).status_code,409)
            self.assertTrue(fresh.state['running'])
            self.assertEqual(self.a.post('/stop').status_code,200);original=fresh
        self.assertIs(other,self.reg.items[self.tb]['coach'])
    def test_camera_reset_does_not_discard_failed_save(self):
        old=self.reg.items[self.ta]['coach'];old.state['summary']={'save_error':True}
        self.assertEqual(self.a.post('/camera/recover',headers={'X-Set-ID':old.state['set_id']}).status_code,409)
        self.assertIs(old,self.reg.items[self.ta]['coach'])
    def test_remote_cannot_reset_all_sessions(self):
        self.assertEqual(self.a.post('/local/cameras/reset',environ_overrides={'REMOTE_ADDR':'192.168.1.10'}).status_code,403)
    def test_admin_bootstrap_requires_existing_account(self):
        with self.assertRaises(ValueError):community.grant_admin(self.store,'not-registered@example.com')
    def test_permanent_host_is_public_but_admin_and_health_stay_private(self):
        with patch.object(server,'STABLE_PUBLIC_URL','https://fitness.example.com'),patch.object(server,'PUBLIC_URL','https://fitness.example.com'),patch.object(server,'PUBLIC_HOST','fitness.example.com'):
            c=server.app.test_client()
            kw=dict(base_url='https://fitness.example.com',environ_overrides={'REMOTE_ADDR':'203.0.113.2'})
            self.assertEqual(c.get('/',**kw).status_code,200)
            self.assertIn(b'https://fitness.example.com/45-fitness-coach',c.get('/sitemap.xml',**kw).data)
            self.assertEqual(c.get('/admin/accounts',**kw).status_code,401)
            self.assertEqual(c.get(f'/profiles/{self.pa}/overview',**kw).status_code,401)
            self.assertEqual(c.post('/session',headers={'Origin':'https://evil.example.com'},**kw).status_code,403)
            self.assertEqual(c.post('/local/cameras/reset',**kw).status_code,403)
    def test_malformed_social_payload_does_not_mutate(self):
        self.assertEqual(self.a.post('/social/friends',json=[]).status_code,400)
        self.assertEqual(self.a.get('/social/friends').json['requests'],[])
    def test_clips_support_seek_ranges(self):
        c=server.app.test_client()
        for name in ['arm','chest','leg','shoulder']:
            r=c.get('/static/videos/'+name+'.mp4',headers={'Range':'bytes=0-63'})
            self.assertEqual(r.status_code,206);self.assertEqual(len(r.data),64);r.close()

if __name__=='__main__':unittest.main()
