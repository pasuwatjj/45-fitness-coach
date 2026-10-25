"""Isolated administrator operations and exchange invariants."""
import unittest,uuid,sqlite3
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import administration as m,community,accounts,training_economy as economy,character
from leaderboard import LeaderboardStore
from test_v13 import RouteTests
import app as server

class AdminTests(unittest.TestCase):
    setUp=RouteTests.setUp
    def setup_admin(self):
        self.actor=int(self.owner.split(':')[1]);self.target=int(self.reg.items[self.tb]['owner'].split(':')[1]);community.schema(self.store)
        with self.store.connect() as db:db.execute("INSERT INTO account_roles VALUES(?,'admin')",(self.actor,))
    def payload(self,**kw):return dict(request_id=str(uuid.uuid4()),target_profile_id=self.pb,currency='beginner',amount=1000,reason='QA adjustment',**kw)
    def post(self,data,uid=None):return self.a.post('/admin/accounts/'+str(uid or self.target)+'/coins',json=data)
    def test_access_validation_and_four_currencies_self_other(self):
        self.setup_admin()
        guest=server.app.test_client();token=guest.post('/session',json={}).json['session_token'];guest.environ_base['HTTP_X_COACH_SESSION']=token
        for endpoint in ['wallets','coins','ban']:
            path=f'/admin/accounts/{self.target}/{endpoint}'
            response=guest.get(path) if endpoint=='wallets' else guest.post(path,json={})
            self.assertEqual(response.status_code,401)
        for path in ['/admin/accounts','/admin/management-history','/admin/exchange-history',f'/admin/accounts/{self.target}/wallets']:
            self.assertEqual(self.b.get(path).status_code,403);self.assertIn(server.app.test_client().get(path).status_code,[401,403])
        for action in ['coins','ban']:self.assertEqual(self.b.post(f'/admin/accounts/{self.target}/{action}',json={'admin':True}).status_code,403)
        before=character.growth(self.store,self.pb)
        for target,pid in [(self.actor,self.pa),(self.target,self.pb)]:
            for currency in economy.CURRENCIES:
                d=self.payload();d.update(target_profile_id=pid,currency=currency,amount=12)
                self.assertEqual(self.post(d,target).status_code,200)
                d.update(request_id=str(uuid.uuid4()),amount=-2);self.assertEqual(self.post(d,target).json['audit']['after_value'],10)
        self.assertEqual(character.growth(self.store,self.pb),before)
        for field,values in [('amount',[0,True,1.5,'2',None,1000001,-11,float('inf'),float('nan')]),('currency',['gold',[],None]),('target_profile_id',[self.pa,True,'2',999999]),('reason',['',' '*4,True,'x'*501]),('request_id',['bad',None])]:
            for value in values:
                d=self.payload();d[field]=value
                with self.subTest(field=field,value=value):self.assertEqual(self.post(d).status_code,400)
        self.assertEqual(self.post(self.payload(),999999).status_code,400)
        self.assertEqual(len(self.a.get('/admin/management-history').json['history']),16)
    def test_atomic_rollback_replay_conflict_concurrent_durable(self):
        self.setup_admin();d=self.payload()
        with self.store.connect() as db:
            m.schema(db);db.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON management_audit BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):m.mutate(self.store,self.actor,self.target,d,'coins')
        with self.store.connect() as db:
            self.assertEqual(economy.balance(db,self.pb)['beginner'],0);db.execute('DROP TRIGGER reject_audit')
        def run(_):return m.mutate(LeaderboardStore(self.store.path),self.actor,self.target,d,'coins')
        with ThreadPoolExecutor(max_workers=5) as pool:rows=list(pool.map(run,range(10)))
        self.assertEqual(sum(not r['replayed'] for r in rows),1)
        self.assertTrue(self.post(d).json['replayed']);changed=dict(d,amount=999);self.assertEqual(self.post(changed).status_code,409)
        with LeaderboardStore(self.store.path).connect() as db:self.assertEqual(economy.balance(db,self.pb)['beginner'],1000)
        with self.store.connect() as db:db.execute("INSERT INTO training_ledger VALUES('limit',?,'expert',?,'test',0)",(self.pb,m.MAX_BALANCE))
        d=self.payload();d.update(currency='expert',amount=1);self.assertEqual(self.post(d).status_code,400)
    def test_ban_existing_session_login_unban_self_and_revoked_admin(self):
        self.setup_admin();d=dict(request_id=str(uuid.uuid4()),banned=True,reason='QA suspension');url=f'/admin/accounts/{self.target}/ban'
        self.assertEqual(self.a.post(f'/admin/accounts/{self.actor}/ban',json=d).status_code,400)
        self.assertEqual(self.a.post(url,json=d).status_code,200);self.assertTrue(self.a.post(url,json=d).json['replayed'])
        for path in ['/profiles','/session',f'/profiles/{self.pb}/character']:
            self.assertEqual(self.b.post(path,json={}).status_code,403)
        with self.store.connect() as db:email=db.execute('SELECT email FROM accounts WHERE id=?',(self.target,)).fetchone()[0]
        with self.assertRaises(ValueError):accounts.login(self.store,dict(email=email,password='Testing-pass-123'))
        d.update(request_id=str(uuid.uuid4()),banned=False);self.assertEqual(self.a.post(url,json=d).status_code,200)
        self.assertEqual(self.b.get('/profiles').status_code,200);self.assertEqual(accounts.login(self.store,dict(email=email,password='Testing-pass-123'))['id'],self.target)
        with self.store.connect() as db:db.execute('DELETE FROM account_roles WHERE account_id=?',(self.actor,))
        self.assertEqual(self.post(self.payload()).status_code,403)
        with self.assertRaises(PermissionError):m.mutate(self.store,self.actor,self.target,self.payload(),'coins')
    def test_exchange_deducts_source_atomic_and_real_history(self):
        self.setup_admin();owner='account:'+str(self.target)
        for c,rate in economy.RATES.items():
            d=self.payload();d.update(currency=c,amount=rate*2);self.assertEqual(self.post(d).status_code,200)
            op=dict(request_id=str(uuid.uuid4()),action='exchange',currency=c,quantity=2)
            result=economy.act(self.store,owner,self.pb,op);self.assertEqual(result['wallet'][c],0)
            self.assertEqual(economy.act(self.store,owner,self.pb,op)['wallet'],result['wallet'])
        self.assertEqual(result['wallet']['universal'],6)
        history=self.a.get('/admin/exchange-history').json['history'];self.assertEqual(len(history),3)
        self.assertEqual({(r['currency'],r['spent'],r['received']) for r in history},{(c,v*2,2) for c,v in economy.RATES.items()})
        d=self.payload();self.post(d)
        with self.store.connect() as db:db.execute("CREATE TRIGGER fail_universal BEFORE INSERT ON training_ledger WHEN NEW.currency='universal' BEGIN SELECT RAISE(ABORT,'fail'); END")
        with self.assertRaises(sqlite3.IntegrityError):economy.act(self.store,owner,self.pb,dict(request_id=str(uuid.uuid4()),action='exchange',currency='beginner',quantity=1))
        with self.store.connect() as db:self.assertEqual(economy.balance(db,self.pb)['beginner'],1000)

if __name__=='__main__':unittest.main()
