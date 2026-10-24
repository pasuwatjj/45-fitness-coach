"""v28 persistence and release coherence regressions; local synthetic accounts only."""
import re,unittest
from pathlib import Path
from unittest.mock import patch
import app as server
import accounts,character
from leaderboard import LeaderboardStore
from sessions import SessionRegistry
import test_v13 as fixtures

class V28Tests(unittest.TestCase):
    setUp=fixtures.RouteTests.setUp
    def test_two_registered_accounts_survive_logout_login_and_server_restart(self):
        emails=[accounts.lookup(self.store,c.get_cookie(accounts.COOKIE).value)['email'] for c in (self.a,self.b)]
        styles=[dict(character.DEFAULT,gender='female',hair='ponytail',skin_color='#aabbcc'),dict(character.DEFAULT,hair='curly',hair_color='#ee2211',shorts_color='#3377ff')]
        for client,profile,style in zip((self.a,self.b),(self.pa,self.pb),styles):
            self.assertEqual(client.post(f'/profiles/{profile}/character',json={'appearance':style}).status_code,200)
            self.assertEqual(client.post('/auth/logout').status_code,200)
        fresh=LeaderboardStore(self.store.path);registry=SessionRegistry(lambda:server.BrowserCoach(fresh));self.addCleanup(registry.stop_all)
        with patch.object(server,'store',fresh),patch.object(server,'sessions',registry):
            # Use the SAME browser across both logins to catch guest/shared-device leakage.
            client=server.app.test_client()
            for index in (1,0,1,0):
                server.auth_attempts.clear()
                self.assertEqual(client.post('/auth/login',json={'email':emails[index],'password':'Testing-pass-123'}).status_code,200)
                session=client.post('/session',json={'auto_profile':True}).json
                client.environ_base['HTTP_X_COACH_SESSION']=session['session_token']
                profile=(self.pa,self.pb)[index];other=(self.pb,self.pa)[index]
                self.assertEqual(client.get(f'/profiles/{profile}/character').json['appearance'],styles[index])
                self.assertEqual(client.get(f'/profiles/{other}/character').status_code,404)
                self.assertEqual(client.post(f'/profiles/{other}/character',json={'appearance':styles[index]}).status_code,404)
                self.assertEqual(client.post('/auth/logout').status_code,200)
                guest=client.post('/session',json={'auto_profile':True}).json
                client.environ_base['HTTP_X_COACH_SESSION']=guest['session_token']
                self.assertTrue(guest['guest'])
                self.assertEqual(client.get(f'/profiles/{guest["default_profile"]["id"]}/character').json['appearance'],character.DEFAULT)
                self.assertEqual(client.post(f'/profiles/{guest["default_profile"]["id"]}/character',json={'appearance':styles[index]}).status_code,403)
    def test_all_local_code_assets_match_current_release_and_exist(self):
        response=self.a.get('/45-fitness-coach');self.assertIn('no-store',response.headers['Cache-Control'])
        urls=re.findall(r'(?:src|href)="(/static/[^" ]+\.(?:css|js)(?:\?[^" ]*)?)"',response.get_data(as_text=True))
        self.assertGreater(len(urls),25)
        for url in urls:
            self.assertTrue(url.endswith('?v='+str(server.GENTLE_COACH_VERSION)),url)
            asset=self.a.get(url);self.assertEqual(asset.status_code,200,url);asset.close()
            self.assertIn('must-revalidate',asset.headers['Cache-Control'])
        self.assertEqual(server.GENTLE_COACH_VERSION,29)
    def test_inactive_vip_data_and_qr_file_remain_available(self):
        for client in (self.a,self.b):
            response=client.get('/vip');self.assertEqual(response.status_code,200);self.assertFalse(response.json['active'])
            response=client.get('/static/images/store/payment-qr.png');self.assertEqual(response.status_code,200);self.assertEqual(response.mimetype,'image/png');self.assertGreater(len(response.data),1000);response.close()

if __name__=='__main__':unittest.main()
