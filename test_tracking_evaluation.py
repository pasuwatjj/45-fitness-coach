import unittest
from tracking_evaluation import evaluate
from test_v32 import AdminTests
class Evaluation(unittest.TestCase):
 def data(self):return dict(name='QA',exercise='curl right',reference='synthetic unit test',reps=[dict(truth='wrong',result='rejected')]*18+[dict(truth='wrong',result='accepted'),dict(truth='wrong',result='unverified')],angles=[dict(sample='frame1 elbow2D',reference=90,measured=94),dict(sample='frame2 elbow2D',reference=100,measured=97)])
 def test_calculations(self):
  d=evaluate(self.data());self.assertEqual(d['wrong_detection'],90);self.assertEqual(d['coverage'],95);self.assertIsNone(d['accuracy']);self.assertEqual(d['mae'],3.5);self.assertEqual(d['bias'],.5);self.assertEqual(d['rmse'],3.536)
 def test_invalid(self):
  for d in [{},dict(self.data(),angles=[dict(sample='x',reference=90,measured=float('nan'))]),dict(self.data(),reps=[dict(truth='wrong',result='unknown')])]:
   with self.assertRaises(ValueError):evaluate(d)
class Routes(AdminTests):
 def test_access_persistence(self):
  self.setup_admin();payload=Evaluation().data()
  self.assertEqual(self.b.get('/admin/tracking-evaluations').status_code,403)
  self.assertEqual(self.b.post('/admin/tracking-evaluations',json=payload).status_code,403)
  self.assertEqual(self.a.post('/admin/tracking-evaluations',json=payload).status_code,200)
  self.assertEqual(self.a.get('/admin/tracking-evaluations').json['records'][0]['result']['wrong_detection'],90)
  self.assertEqual(self.a.post('/admin/tracking-evaluations',json={}).status_code,400)
