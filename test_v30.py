"""v30 account identity, legacy preservation and localization regressions."""
import tempfile, unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import app as server
import sessions, visitors, community, membership
from leaderboard import LeaderboardStore
from test_sessions import authorize_client

class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=LeaderboardStore(Path(self.tmp.name)/'test.db')
        self.registry=sessions.SessionRegistry(lambda:server.BrowserCoach(self.store))
        for name,value in [('store',self.store),('sessions',self.registry)]:
            p=patch.object(server,name,value);p.start();self.addCleanup(p.stop)
        self.a=server.app.test_client();self.b=server.app.test_client()
        authorize_client(server,self.a,'owner@example.com');authorize_client(server,self.b,'other@example.com')
        self.profile=self.a.post('/profiles',json={'name':'Original'}).json['profile']
    def test_duplicate_blocked_rename_owned_persistent_history(self):
        pid=self.profile['id']
        self.store.save_set('old-set',pid,'curl','both',8,0,4,4,{})
        self.assertEqual(self.a.post('/profiles',json={'name':'Second'}).status_code,400)
        self.assertEqual(self.b.post(f'/profiles/{pid}/name',json={'name':'Stolen'}).status_code,404)
        self.assertEqual(self.a.post(f'/profiles/{pid}/name',json={'name':'New Name'}).status_code,200)
        self.assertEqual(self.a.get('/profiles').json['profiles'],[{'id':pid,'name':'New Name'}])
        self.assertEqual(self.a.get(f'/profiles/{pid}/overview').json['totals']['reps'],8)
        client=server.app.test_client();server.auth_attempts.clear()
        self.assertEqual(client.post('/auth/login',json={'email':'owner@example.com','password':'Testing-pass-123'}).status_code,200)
        response=client.post('/session',json={'auto_profile':True});client.environ_base['HTTP_X_COACH_SESSION']=response.json['session_token']
        self.assertEqual(response.json['default_profile']['name'],'New Name')
        self.assertEqual(len(client.get('/profiles').json['profiles']),1)
    def test_legacy_ids_history_retained_and_primary_stable_after_rename(self):
        owner=self.registry.items[self.a.environ_base['HTTP_X_COACH_SESSION']]['owner']
        with self.store.connect() as db:
            pid=db.execute("INSERT INTO profiles(name) VALUES('AAA Legacy')").lastrowid
            db.execute('INSERT INTO profile_owners VALUES(?,?)',(pid,owner))
        self.store.save_set('legacy-set',pid,'curl','both',6,0,3,3,{})
        data=self.a.get('/profiles').json
        self.assertEqual(data['primary_profile_id'],self.profile['id']);self.assertEqual(len(data['profiles']),2)
        self.assertEqual(self.a.post(f'/profiles/{pid}/name',json={'name':'Other Name'}).status_code,400)
        self.assertEqual(self.a.get(f'/profiles/{pid}/overview').json['totals']['reps'],6)
        self.a.post(f"/profiles/{self.profile['id']}/name",json={'name':'ZZZ'})
        self.assertEqual(visitors.ensure_profile(self.store,owner)['id'],self.profile['id'])
    def test_parallel_create_and_auto_profile_only_create_once(self):
        def attempt(i):
            try:return sessions.add_profile(self.store,'account:999',f'Concurrent {i}')
            except ValueError:return None
        with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(attempt,range(12)))
        self.assertEqual(sum(x is not None for x in results),1)
        with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(lambda _:visitors.ensure_profile(self.store,'guest:parallel'),range(12)))
        self.assertEqual(len({x['id'] for x in results}),1)
    def test_name_validation_and_duplicate_name(self):
        p=self.b.post('/profiles',json={'name':'Taken'}).json['profile']
        for value in ['',None,'x'*31,'bad\x00name','Taken']:
            self.assertEqual(self.a.post(f"/profiles/{self.profile['id']}/name",json={'name':value}).status_code,400)
        self.assertEqual(self.store.profile(self.profile['id'])['name'],'Original')
    def test_public_role_flags_no_email(self):
        owner=self.registry.items[self.a.environ_base['HTTP_X_COACH_SESSION']]['owner']
        community.grant_admin(self.store,'owner@example.com')
        with self.store.connect() as db:
            membership.schema(db)
            db.execute('INSERT INTO vip_memberships(owner,expires) VALUES(?,?)',(owner,9999999999))
        row=community.profile_roles(self.store,[dict(self.profile)])[0]
        self.assertTrue(row['admin']);self.assertTrue(row['vip']);self.assertNotIn('email',row)

class TranslationTests(unittest.TestCase):
    def test_no_partial_thai_word_replacement(self):
        import localization
        self.assertNotIn('Chest',localization.english('ออกกำลังกาย'))
        self.assertEqual(localization.english('อก'),'Chest')
        self.assertEqual(localization.english('ขออกทดสอบ'),'ขออกทดสอบ')
    def test_no_top_home_button_and_correct_asset_links(self):
        html=server.app.test_client().get('/').get_data(as_text=True)
        self.assertNotIn('id="backHome"',html)
        self.assertIn('id="homeTab"',html)
        self.assertIn('/static/v30.css?v=32',html)

if __name__=='__main__':unittest.main()
