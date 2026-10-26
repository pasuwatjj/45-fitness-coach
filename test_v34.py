import unittest,json
from test_v13 import RouteTests
from angles import SetAngles,save,history
from progress_analysis import report
import character
class AnalyticsTests(unittest.TestCase):
 setUp=RouteTests.setUp
 def track(self):
  a=SetAngles()
  for now,x in [(0,160),(100,150),(500,90),(900,50),(1300,100),(1700,160)]:a.sample('right',dict(elbow=x,torso_arm=12,arm=12,lean=0),'2D',now,moving=now>0)
  a.completed('right','2D');return a
 def test_timing_range_gaps(self):
  a=self.track();r=a.report()[0];self.assertEqual(r['repetitions'][0]['seconds'],1.6);self.assertEqual(r['repetitions'][0]['range'],110);self.assertEqual(r['metrics']['torso_arm']['mean'],12)
  a.invalidate();a.sample('right',dict(elbow=150),'2D',3000,True);a.sample('right',dict(elbow=60),'2D',3300,True);a.completed('right','2D');self.assertEqual(len(a.report()[0]['repetitions']),1)
 def test_reset_access_preserve_and_new(self):
  self.store.save_set('earned',self.pa,'curl','right',10,0,0,10,{},difficulty='beginner')
  save(self.store,'old',self.pa,'curl',self.track());save(self.store,'other',self.pb,'curl',self.track());before=character.growth(self.store,self.pa)
  self.assertEqual(self.b.post(f'/profiles/{self.pa}/analytics/reset',json={'confirm':True}).status_code,404)
  for data in [[],None,{'confirm':False}]:self.assertEqual(self.a.post(f'/profiles/{self.pa}/analytics/reset',json=data).status_code,400)
  c=self.reg.items[self.ta]['coach'];c.state['profile']=self.store.profile(self.pa);c.state['set_id']='active'
  self.assertEqual(self.a.post(f'/profiles/{self.pa}/analytics/reset',json={'confirm':True}).status_code,200)
  self.assertEqual(report(self.store,self.pa)['sets'],[]);self.assertTrue(report(self.store,self.pb)['sets']);self.assertEqual(character.growth(self.store,self.pa),before)
  with self.store.connect() as db:self.assertEqual(db.execute('SELECT reps FROM workout_sets WHERE id=?',('earned',)).fetchone()[0],10)
  save(self.store,'active',self.pa,'curl',self.track());self.assertEqual(report(self.store,self.pa)['sets'],[])
  save(self.store,'new',self.pa,'curl',self.track());self.assertEqual(len(report(self.store,self.pa)['sets']),1);self.assertEqual(len(history(self.store,self.pa)['sets']),1)
 def test_legacy_and_small_history(self):
  a=self.track();rows=a.report();rows[0].pop('repetitions');rows[0]['metrics'].pop('torso_arm');save(self.store,'old',self.pa,'curl',a)
  with self.store.connect() as db:db.execute('UPDATE set_angles SET data=? WHERE id=?',(json.dumps(rows),'old'))
  r=report(self.store,self.pa)['sets'][0];self.assertIsNone(r['alignment']);self.assertEqual(r['repetitions'],[]);self.assertEqual(r['rom'],110)
if __name__=='__main__':unittest.main()
