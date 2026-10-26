import unittest
from types import SimpleNamespace as P
from side_tracking import SideTracking
from training_modes import ArmSelector

def pose():return [P(x=.5,y=.5,visibility=1.,presence=1.) for _ in range(33)]
class SideTests(unittest.TestCase):
 def test_measured_confidence_dip_not_unlimited_or_invented(self):
  for side,ids in [('left',(11,13,15,23)),('right',(12,14,16,24))]:
   p=pose();g=SideTracking();self.assertTrue(g.accepts(side,p,ids,0))
   for i in ids:p[i].visibility=.55
   self.assertTrue(g.accepts(side,p,ids,300));self.assertFalse(g.accepts(side,p,ids,401));self.assertFalse(g.accepts(side,p,ids,450))
 def test_missing_jump_nonfinite_and_offscreen_cancel(self):
  for attr,value in [('visibility',.1),('presence',.1),('x',float('nan')),('x',1.1),('x',.7)]:
   p=pose();g=SideTracking();g.accepts('right',p,(12,14,16,24),0);p[16].visibility=.55;setattr(p[16],attr,value)
   self.assertFalse(g.accepts('right',p,(12,14,16,24),100))
 def test_both_sides_independent_and_far_side_not_required(self):
  p=pose();g=SideTracking()
  for i in (11,13,15,23):p[i].visibility=.1
  self.assertTrue(g.accepts('right',p,(12,14,16,24),0));self.assertFalse(g.accepts('left',p,(11,13,15,23),0))
 def test_auto_prefers_workable_side_not_arm_with_hidden_hip(self):
  p=pose();a=ArmSelector();p[24].visibility=.1
  for t in (0,200,500):out=a.choose(p,t,include_hip=True)
  self.assertEqual(out,('left',True))
 def test_reset_prevents_reuse(self):
  p=pose();g=SideTracking();g.accepts('right',p,(12,14,16,24),0);g.clear()
  p[16].visibility=.55;self.assertFalse(g.accepts('right',p,(12,14,16,24),100))
if __name__=='__main__':unittest.main()

class ProcessTests(unittest.TestCase):
 def test_confidence_dip_preserves_tracking_but_occlusion_cancels_cycle(self):
  import tempfile
  from pathlib import Path
  import numpy as np
  import app as server
  from leaderboard import LeaderboardStore
  from test_v11 import landmarks
  from types import SimpleNamespace as NS
  with tempfile.TemporaryDirectory() as d:
   c=server.BrowserCoach(LeaderboardStore(Path(d)/'db'));c.configure('right',10,'upper','curl');c.state.update(running=True,paused=False)
   frame=np.zeros((480,640,3),dtype=np.uint8)
   def feed(angle,t,confidence=1):
    p,w=landmarks(angle)
    for i in (12,14,16,24):p[i].visibility=confidence
    c.process(frame,NS(pose_landmarks=[p],pose_world_landmarks=[w]),t)
   feed(160,1000);feed(160,1200);feed(140,1300,.55)
   self.assertIsNotNone(c.state['angle']);self.assertEqual(c.forms['right'].counter.phase,'ready')
   feed(80,1400,.1);self.assertEqual(c.forms['right'].counter.phase,'waiting')
   feed(60,1500);feed(60,1700);feed(160,1800);feed(160,2000)
   self.assertEqual(c.state['reps'],0)
 def test_profile_view_near_arm_tracks_without_fabricating_far_arm(self):
  import tempfile
  from pathlib import Path
  import numpy as np
  import app as server
  from leaderboard import LeaderboardStore
  from test_v11 import landmarks
  from test_v24 import rotate,project
  from types import SimpleNamespace as NS
  for near,far in [('right','left'),('left','right')]:
   with tempfile.TemporaryDirectory() as d:
    c=server.BrowserCoach(LeaderboardStore(Path(d)/'db'));c.configure('both',10,'upper','curl');c.state.update(running=True,paused=False)
    _,w=landmarks(150);w=rotate(w,90);p=project(w)
    for i in ((11,13,15,23) if far=='left' else (12,14,16,24)):p[i].visibility=.1
    c.process(np.zeros((480,640,3),dtype=np.uint8),NS(pose_landmarks=[p],pose_world_landmarks=[w]),1000)
    self.assertIsNotNone(c.outputs[near]['angle']);self.assertIsNone(c.outputs[far]['angle']);self.assertEqual(c.state['reps'],0)
