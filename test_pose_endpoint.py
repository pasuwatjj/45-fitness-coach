import unittest
from test_v13 import RouteTests
import app as server
class PoseEndpoint(unittest.TestCase):
 setUp=RouteTests.setUp
 def test_boundaries_and_pause(self):
  p=dict(width=640,height=480,pose=[],world=[],hands=[],handWorld=[])
  self.assertIn(server.app.test_client().post('/pose-frame',json=p).status_code,(401,403))
  self.assertEqual(self.a.post('/pose-frame',json={}).status_code,400)
  self.assertEqual(self.a.post('/pose-frame',json=dict(p,extra='x'*61000)).status_code,413)
  self.assertEqual(self.a.post('/start',json=dict(profile_id=self.pa,exercise='curl',arm='right')).status_code,200)
  c=self.reg.items[self.ta]['coach'];headers={'X-Set-ID':c.state['set_id']}
  self.assertEqual(self.b.post('/pose-frame',json=p,headers=headers).status_code,409)
  c.last_local_request=0;r=self.a.post('/pose-frame',json=p,headers=headers);self.assertEqual(r.status_code,200);self.assertEqual(r.json['state']['reps'],0)
  self.a.post('/pause',json={});c.last_local_request=0;r=self.a.post('/pose-frame',json=p,headers=headers);self.assertEqual(r.status_code,200);self.assertTrue(r.json['state']['paused']);self.assertEqual(r.json['state']['reps'],0)
