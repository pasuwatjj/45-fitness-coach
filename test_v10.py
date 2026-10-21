import io,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import app as server
from leaderboard import LeaderboardStore
from sessions import SessionRegistry
from test_sessions import authorize_client

class PrivateProfileDashboard(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=LeaderboardStore(Path(self.temp.name)/'db')
        self.registry=SessionRegistry(lambda:server.BrowserCoach(self.store))
        self.patches=[patch.object(server,'store',self.store),patch.object(server,'sessions',self.registry)]
        for p in self.patches:p.start()
        self.addCleanup(self.clean)
        self.a=server.app.test_client();self.b=server.app.test_client()
        authorize_client(server,self.a);authorize_client(server,self.b)
        self.pa=self.a.post('/profiles',json={'name':'Alpha'}).json['profile']['id']
        self.pb=self.b.post('/profiles',json={'name':'Beta'}).json['profile']['id']
    def clean(self):
        self.registry.stop_all()
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()
    def picture(self):
        out=io.BytesIO();Image.new('RGB',(600,400),'red').save(out,'PNG');return out.getvalue()
    def test_overview_links_only_selected_profile(self):
        self.store.save_set('alpha',self.pa,'curl','right',10,2,0,10,{'tempo':2})
        self.store.save_set('beta',self.pb,'curl','right',99,0,0,99,{})
        response=self.a.get(f'/profiles/{self.pa}/overview');self.assertEqual(response.status_code,200)
        data=response.json;self.assertEqual(data['totals'],dict(sets=1,reps=10,flagged=2))
        self.assertEqual(data['sets'][0]['observations'],{'tempo':2})
        self.assertEqual(data['profile']['name'],'Alpha');self.assertEqual(data['streak']['current'],0)
        self.assertEqual(self.a.get(f'/profiles/{self.pb}/overview').status_code,404)
        self.assertEqual(server.app.test_client().get(f'/profiles/{self.pa}/overview').status_code,401)
    def test_avatar_normalized_private_and_persistent(self):
        path=f'/profiles/{self.pa}/avatar'
        self.assertEqual(self.a.post(path,data=self.picture(),content_type='image/png').status_code,200)
        response=self.a.get(path);self.assertEqual(response.status_code,200)
        self.assertEqual(response.mimetype,'image/jpeg');self.assertIn('no-store',response.headers['Cache-Control'])
        image=Image.open(io.BytesIO(response.data));self.assertEqual(image.size,(384,384));self.assertFalse(image.getexif())
        self.assertEqual(self.b.get(path).status_code,404)
        self.assertEqual(self.b.post(path,data=self.picture()).status_code,404)
        self.assertTrue(self.a.get(f'/profiles/{self.pa}/overview').json['has_avatar'])
        from profile_data import get_avatar
        self.assertEqual(get_avatar(LeaderboardStore(self.store.path),self.pa),response.data)
    def test_invalid_upload_does_not_replace_avatar(self):
        path=f'/profiles/{self.pa}/avatar';self.a.post(path,data=self.picture())
        before=self.a.get(path).data
        self.assertEqual(self.a.post(path,data=b'<svg>not an image</svg>').status_code,400)
        self.assertEqual(self.a.post(path,data=b'x'*(3*1024*1024+1)).status_code,413)
        self.assertEqual(self.a.get(path).data,before)
    def test_avatar_over_one_mb_and_under_three_mb_is_accepted(self):
        import os
        raw=io.BytesIO();Image.frombytes('RGB',(800,600),os.urandom(800*600*3)).save(raw,'PNG')
        self.assertGreater(len(raw.getvalue()),1024*1024)
        self.assertEqual(self.a.post(f'/profiles/{self.pa}/avatar',data=raw.getvalue(),content_type='image/png').status_code,200)

if __name__=='__main__':unittest.main()
