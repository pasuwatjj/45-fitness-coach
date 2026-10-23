"""Payment outcomes, VIP enforcement, coin transactions and receipt privacy."""
import copy
import io
import os
import tempfile
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch,MagicMock
from PIL import Image
import app as server
import membership as vip
import shop
import challenges
from leaderboard import LeaderboardStore
from sessions import SessionRegistry
from test_sessions import authorize_client,FakeDetector

def picture(color='red'):
    out=io.BytesIO();Image.new('RGB',(400,500),color).save(out,'PNG');return out.getvalue()

def provider(ref='REFERENCE0001'):
    now=datetime.now(timezone(timedelta(hours=7)))
    return {'success':True,'data':dict(success=True,amount=50,countryCode='TH',paidLocalCurrency='764',
        sendingBank='004',receivingBank='004',transRef=ref,transDate=now.strftime('%Y%m%d'),
        transTime=now.strftime('%H:%M:%S'),receiver={'account':{'value':'xxx-x-x4148-x'}})}

class PaymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=LeaderboardStore(Path(self.tmp.name)/'db')
    def test_missing_configuration_closes_payments(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertFalse(vip.status(self.store,'account:1')['payment_ready'])
            with self.assertRaises(ValueError):vip.submit(self.store,'account:1','a@example.com',picture())
    def test_exact_amount_bank_receiver_date_and_currency(self):
        self.assertEqual(vip.validate_result(provider()),'004:REFERENCE0001')
        for field,value in [('amount',49),('receivingBank','006'),('countryCode','US'),('paidLocalCurrency','840'),('transDate','20200101'),('success',False),('transRef','')]:
            bad=provider();bad['data'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):vip.validate_result(bad)
        for account in ['xxx-x-x9999-x','xxxxxxxxxx','1191841489']:
            bad=provider();bad['data']['receiver']['account']['value']=account
            with self.assertRaises(ValueError):vip.validate_result(bad)
    def test_provider_duplicate_payload_never_grants(self):
        response=MagicMock(status_code=400);response.json.return_value=dict(provider(),code=1012)
        with patch.dict(os.environ,{'FITNESS_SLIPOK_BRANCH':'1','FITNESS_SLIPOK_KEY':'fake'}),patch.object(vip.requests,'post',return_value=response) as call:
            with self.assertRaises(ValueError):vip.verify_slip(picture())
            self.assertEqual(call.call_args.kwargs['data'],{'log':'true','amount':'50'})
            self.assertFalse(call.call_args.kwargs['allow_redirects'])
    def test_verified_image_duplicate_transaction_and_renewal(self):
        with patch.object(vip,'payment_ready',return_value=True),patch.object(vip,'verify_slip',return_value='004:PAY1'):
            d=vip.submit(self.store,'account:1','a@example.com',picture());expires=d['expires']
            self.assertTrue(d['active']);self.assertAlmostEqual(expires-time.time(),30*86400,delta=3)
            self.assertEqual(vip.submit(self.store,'account:1','a@example.com',picture())['expires'],expires)
            bad=vip.submit(self.store,'account:2','b@example.com',picture('blue'))
            self.assertFalse(bad['active']);self.assertEqual(bad['receipts'][0]['status'],'review')
        with patch.object(vip,'payment_ready',return_value=True),patch.object(vip,'verify_slip',return_value='004:PAY2'):
            d=vip.submit(self.store,'account:1','a@example.com',picture('green'))
            self.assertAlmostEqual(d['expires'],expires+30*86400,delta=1)
    def test_failed_verification_and_delayed_retry(self):
        with patch.object(vip,'payment_ready',return_value=True),patch.object(vip,'verify_slip',side_effect=ValueError('bank delay')):
            d=vip.submit(self.store,'account:1','a@example.com',picture());self.assertFalse(d['active'])
            with self.assertRaises(ValueError):vip.submit(self.store,'account:1','a@example.com',picture())
        with self.store.connect() as db:db.execute('UPDATE vip_receipts SET last_check=0')
        with patch.object(vip,'payment_ready',return_value=True),patch.object(vip,'verify_slip',return_value='004:RETRY1'):
            self.assertTrue(vip.submit(self.store,'account:1','a@example.com',picture())['active'])
    def test_mail_goes_to_fixed_owner_with_private_attachment(self):
        with patch.object(vip,'payment_ready',return_value=True),patch.object(vip,'verify_slip',return_value='004:MAIL1'):
            vip.submit(self.store,'account:1','a@example.com',picture())
        env={'FITNESS_SMTP_HOST':'example.test','FITNESS_SMTP_USER':'sender@example.com','FITNESS_SMTP_PASSWORD':'fake','FITNESS_SMTP_PORT':'587'}
        with patch.dict(os.environ,env),patch.object(vip.smtplib,'SMTP') as smtp:
            vip.send_pending(self.store)
            client=smtp.return_value.__enter__.return_value
            client.starttls.assert_called_once()
            message=client.send_message.call_args.args[0]
            self.assertEqual(message['To'],'67011241@kmitl.ac.th')
            self.assertEqual(len(list(message.iter_attachments())),1)
            self.assertEqual(vip.status(self.store,'account:1')['receipts'][0]['mail_status'],'sent')
    def test_mail_failure_keeps_verified_vip_and_queues_retry(self):
        with patch.object(vip,'payment_ready',return_value=True),patch.object(vip,'verify_slip',return_value='004:MAILFAIL'):
            vip.submit(self.store,'account:1','a@example.com',picture())
        with patch.object(vip,'mail_ready',return_value=True),patch.dict(os.environ,{'FITNESS_SMTP_USER':'a@example.com'}):
            vip.send_pending(self.store)
        d=vip.status(self.store,'account:1');self.assertTrue(d['active']);self.assertEqual(d['receipts'][0]['mail_status'],'queued')
    def test_invalid_file_is_not_stored(self):
        with self.assertRaises(ValueError):vip.normalize_image(b'<svg>fake receipt</svg>')

class CommerceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=LeaderboardStore(Path(self.tmp.name)/'db');self.p=self.store.create_profile('One')['id']
        with self.store.connect() as db:
            shop.schema(db);db.execute('INSERT INTO vip_memberships VALUES(?,?)',('account:1',time.time()+86400))
            db.execute("INSERT INTO reward_ledger(id,profile_id,amount,kind) VALUES('earned',?,1000,'workout')",(self.p,))
    def convert(self,key=None,quantity=1):return shop.act(self.store,'account:1',self.p,dict(action='convert',request_id=key or str(uuid.uuid4()),quantity=quantity))
    def order(self,key=None):return shop.act(self.store,'account:1',self.p,dict(action='redeem',request_id=key or str(uuid.uuid4()),name='Tester',phone='0800000000',address='Test address'))
    def test_conversion_retry_and_purple_balance_consistency(self):
        key=str(uuid.uuid4());self.convert(key);d=self.convert(key)
        self.assertEqual((d['gold'],d['purple']),(990,1));self.assertEqual(challenges.overview(self.store,self.p)['purple_coins'],1)
        with self.assertRaises(ValueError):self.convert(key,2)
    def test_redeem_reserve_duplicate_cancel_refund_once(self):
        self.convert(quantity=50);key=str(uuid.uuid4());self.order(key);d=self.order(key)
        self.assertEqual(d['purple'],0);self.assertEqual(len(d['orders']),1)
        with self.assertRaises(ValueError):shop.resolve(self.store,key,'cancelled','account:2')
        for _ in range(2):shop.resolve(self.store,key,'cancelled','account:1')
        self.assertEqual(shop.overview(self.store,'account:1',self.p)['purple'],50)
    def test_fulfilled_order_cannot_refund(self):
        self.convert(quantity=50);key=str(uuid.uuid4());self.order(key);shop.resolve(self.store,key,'fulfilled')
        with self.assertRaises(ValueError):shop.resolve(self.store,key,'cancelled','account:1')
    def test_expired_and_nonvip_conversion_denied(self):
        with self.store.connect() as db:db.execute('UPDATE vip_memberships SET expires=0')
        with self.assertRaises(PermissionError):self.convert()
        self.assertEqual(shop.overview(self.store,'account:1',self.p)['gold'],1000)
    def test_concurrent_spending_cannot_go_negative(self):
        self.convert(quantity=99)
        def attempt(_):
            try:self.convert();return True
            except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
        self.assertEqual(sum(results),1);self.assertEqual(shop.overview(self.store,'account:1',self.p)['gold'],0)

class RouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=LeaderboardStore(Path(self.tmp.name)/'db');self.reg=SessionRegistry(lambda:server.BrowserCoach(self.store))
        self.patches=[patch.object(server,'store',self.store),patch.object(server,'sessions',self.reg),patch.object(server.vision.PoseLandmarker,'create_from_options',side_effect=lambda *_:FakeDetector())]
        for p in self.patches:p.start();self.addCleanup(p.stop)
        self.addCleanup(self.reg.stop_all)
        self.a=server.app.test_client();self.b=server.app.test_client();self.ta=authorize_client(server,self.a);self.tb=authorize_client(server,self.b)
        self.pa=self.a.post('/profiles',json={'name':'A'}).json['profile']['id'];self.pb=self.b.post('/profiles',json={'name':'B'}).json['profile']['id']
        self.owner=self.reg.items[self.ta]['owner']
    def grant(self):
        with self.store.connect() as db:
            vip.schema(db);db.execute('INSERT INTO vip_memberships VALUES(?,?)',(self.owner,time.time()+86400))
    def test_third_of_each_group_locked_and_api_enforced(self):
        expected={ex['id'] for group in server.GROUPS for ex in [list(e for e in server.EXERCISES if e['group']==group)[2]]}
        self.assertEqual(expected,vip.LOCKED)
        for ex in vip.LOCKED:
            self.assertEqual(self.a.post('/start',json=dict(profile_id=self.pa,exercise=ex,arm=server.CATALOG[ex]['default_arm'])).status_code,403)
        self.assertEqual(self.a.get(f'/profiles/{self.pa}/rewards').status_code,403)
        self.grant();self.assertEqual(self.a.post('/start',json=dict(profile_id=self.pa,exercise='front_raise',arm='right')).status_code,200)
        self.assertEqual(self.a.get(f'/profiles/{self.pa}/rewards').status_code,200)
        self.assertEqual(self.b.get(f'/profiles/{self.pa}/rewards').status_code,404)
    def test_calendar_cannot_bypass_vip(self):
        self.store.save_plan_day(self.pa,server.today_thailand().isoformat(),[dict(exercise='front_raise',arm_mode='right',target_sets=1,target_reps=1)])
        self.assertEqual(self.a.post('/plans/today/start',json={'profile_id':self.pa}).status_code,403)
    def test_expiry_blocks_premium_reset_and_resume(self):
        self.grant()
        self.assertEqual(self.a.post('/start',json=dict(profile_id=self.pa,exercise='front_raise',arm='right')).status_code,200)
        with self.store.connect() as db:
            db.execute('UPDATE vip_memberships SET expires=? WHERE owner=?',(time.time()-1,self.owner))
        for route in ('/reset','/resume'):
            self.assertEqual(self.a.post(route,json={}).status_code,403)
    def test_private_slip_and_no_image_only_activation(self):
        with patch.object(vip,'payment_ready',return_value=True),patch.object(vip,'verify_slip',side_effect=ValueError('not a payment')):
            r=self.a.post('/vip/slips',data=picture(),content_type='image/png');self.assertEqual(r.status_code,200)
        self.assertFalse(r.json['active']);rid=r.json['receipts'][0]['id']
        self.assertEqual(self.a.get('/vip/slips/'+rid).status_code,200)
        self.assertEqual(self.b.get('/vip/slips/'+rid).status_code,404)
        self.assertEqual(server.app.test_client().get('/vip').status_code,401)
    def test_client_flags_cannot_grant_vip(self):
        self.assertEqual(self.a.post('/vip',json={'active':True,'expires':9999999999}).status_code,405)
        self.assertFalse(self.a.get('/vip').json['active'])

if __name__=='__main__':unittest.main()
