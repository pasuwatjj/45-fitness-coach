"""Manual tracking retains a moving target without freezing poses or earning missing reps."""
import unittest
from types import SimpleNamespace as P
from person_tracking import PersonLock

def pose(x=.4):
    p=[P(x=x,y=.3,visibility=1) for _ in range(33)]
    for i,dx,y in [(11,-.08,.3),(12,.08,.3),(23,-.06,.65),(24,.06,.65)]:p[i]=P(x=x+dx,y=y,visibility=1)
    return p

class TrackingLock(unittest.TestCase):
    def test_lock_requires_fresh_detection_and_valid_slot(self):
        t=PersonLock()
        with self.assertRaises(ValueError):t.pin(0,True,0)
        t.update([pose()],0)
        for slot,value in [(True,True),(1,True),(0,1)]:
            with self.assertRaises(ValueError):t.pin(slot,value,.1)
        with self.assertRaises(ValueError):t.pin(0,True,2.1)
        t.pin(0,True,.1);self.assertEqual(t.snapshot()['pinned'],[True])
    def test_moving_target_stays_live_and_ignores_candidate_order(self):
        t=PersonLock();t.update([pose(.2)],0);t.pin(0,True,.01)
        for i in range(1,9):
            x=.2+.045*i;self.assertEqual(t.update([pose(.95),pose(x)],i*.1),[1]);self.assertAlmostEqual(t.slots[0][0],x)
        self.assertGreater(t.velocity[0][0],0)
    def test_lock_never_reacquires_a_distant_replacement(self):
        t=PersonLock();t.update([pose(.2)],0);t.pin(0,True,.01)
        self.assertEqual(t.update([],1),[None])
        for i in range(10):self.assertEqual(t.update([pose(.9)],2+i*.1),[None])
        t.pin(0,False,3)
        for i in range(10):selected=t.update([pose(.9)],3+i*.1)
        self.assertEqual(selected,[0])
    def test_missing_and_overlap_frames_never_reuse_a_pose(self):
        t=PersonLock();t.update([pose()],0);t.pin(0,True,.01)
        self.assertEqual(t.update([],.1),[None]);self.assertEqual(t.update([pose(.41)],.2),[0])
        self.assertEqual(t.update([pose(.42),pose(.43)],.3),[None]);self.assertEqual(t.status,['ambiguous']);self.assertTrue(t.pinned[0])
    def test_two_players_can_lock_independently(self):
        t=PersonLock(2);self.assertEqual(t.update([pose(.25),pose(.8)],0),[0,1]);t.pin(0,True,.01);t.pin(1,True,.01)
        self.assertEqual(t.update([pose(.82),pose(.27)],.1),[1,0]);t.pin(0,False,.2);self.assertEqual(t.snapshot()['pinned'],[False,True])



class LockRoutes(unittest.TestCase):
    def setUp(self):
        import test_sessions
        test_sessions.PrivateSessions.setUp(self)
    def cleanup(self):
        import test_sessions
        test_sessions.PrivateSessions.cleanup(self)
    def test_workout_lock_preserves_set_and_counts_is_private_and_resets_on_restart(self):
        import time,app
        self.assertEqual(self.a.post('/start',json={'profile_id':self.pa['id'],'exercise':'curl','arm':'right'}).status_code,200)
        c=self.registry.items[self.ta]['coach'];c.person_lock.update([pose()],time.monotonic());c.forms['right'].counter.reps=7;c.outputs['right']=c.forms['right'].base();c.aggregate();sid=c.state['set_id'];before=c.snapshot()['reps'];self.assertEqual(before,7)
        r=self.a.post('/tracking/lock',json={'slot':0,'locked':True},headers={'X-Set-ID':sid});self.assertEqual(r.status_code,200,r.json);self.assertTrue(r.json['state']['tracking']['pinned'][0]);self.assertEqual(r.json['state']['set_id'],sid);self.assertEqual(r.json['state']['reps'],before)
        self.assertEqual(self.b.post('/tracking/lock',json={'slot':0,'locked':False},headers={'X-Set-ID':sid}).status_code,409)
        self.assertEqual(app.app.test_client().post('/tracking/lock',json={'locked':True}).status_code,401)
        self.assertEqual(self.a.post('/tracking/lock',json={'slot':0,'locked':False},headers={'X-Set-ID':sid}).status_code,200)
        self.a.post('/stop');self.a.post('/start',json={'profile_id':self.pa['id'],'exercise':'curl','arm':'right'});self.assertEqual(c.person_lock.pinned,[False])
    def test_cardio_can_lock_after_detection(self):
        import time
        r=self.a.post('/cardio/start',json={'profile_id':self.pa['id'],'mode':'upper'});self.assertEqual(r.status_code,200,r.json)
        c=self.registry.items[self.ta]['coach'];c.person_lock.update([pose()],time.monotonic())
        r=self.a.post('/tracking/lock',json={'slot':0,'locked':True},headers={'X-Set-ID':c.state['set_id']});self.assertEqual(r.status_code,200,r.json);self.assertTrue(r.json['state']['tracking']['pinned'][0]);self.assertEqual(r.json['state']['cardio']['reps'],0)

if __name__=='__main__':unittest.main()
