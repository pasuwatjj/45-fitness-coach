import unittest,math
from local_pose import parse
from form_rules import FormCoach
from motion_coach import MotionCoach
from exercises import EXERCISES,MOTIONS
import test_planner_motion
from app import SETTINGS,CameraCoach
from unittest.mock import Mock

class V35(unittest.TestCase):
 def test_all_exercises_first_valid_frame_no_dwell_no_free_rep(self):
  helper=test_planner_motion.MotionTests()
  for ex in EXERCISES:
   with self.subTest(ex=ex['id']):
    f=FormCoach(SETTINGS) if ex['family']=='curl' else MotionCoach(ex['id'],SETTINGS)
    m=dict(elbow=100,lean=0,arm=10) if ex['family']=='curl' else helper.values(ex['family'],90)
    o=f.update(m,100)
    self.assertTrue(o['calibrated']);self.assertEqual(o['reps'],0)
 def test_manual_rest_and_planned_completion(self):
  c=object.__new__(CameraCoach);c.state={'reps':2,'paused':False,'plan':None};c.pause=Mock();c.last_activity=0
  c.maybe_rest(1000000);c.pause.assert_not_called()
  c.state['plan']={'target_reps':2};c.maybe_rest(1000000);c.pause.assert_called_once_with(automatic=True)
 def test_pose_validation(self):
  p={'width':640,'height':480,'pose':[],'world':[],'hands':[],'handWorld':[]};self.assertEqual(parse(p)[0],640)
  for bad in [None,{},dict(p,width=999999),dict(p,pose=[{}]),dict(p,hands=[[]])]:
   with self.assertRaises((ValueError,TypeError)):parse(bad)
  point=dict(x=.5,y=.5,z=0,visibility=1);p['pose']=[point]*33;self.assertEqual(len(parse(p)[2].pose_landmarks[0]),33)
  p['pose']=[dict(point,x=math.nan)]*33
  with self.assertRaises(ValueError):parse(p)
if __name__=='__main__':unittest.main()
