"""Camera-yaw invariance and movement gates; synthetic tests are not real-camera validation."""
import math,copy,unittest
from types import SimpleNamespace as P
from unittest.mock import patch
import app as server
from exercises import EXERCISES,thresholds,MOTIONS
from motion_coach import pose_metrics,MotionCoach
from form_rules import FormCoach
from strict_form import geometry
from cardio import PushUpRound,JumpingJackRound
from test_v11 import landmarks
from test_v18 import pose
import test_v13 as fixtures

def rotate(points,degrees):
    out=copy.deepcopy(points);a=math.radians(degrees)
    for q in out:q.x,q.z=q.x*math.cos(a)+q.z*math.sin(a),-q.x*math.sin(a)+q.z*math.cos(a)
    return out

def project(world):
    return [P(x=.5+q.x*.3,y=.25+q.y*.3,z=q.z,visibility=1.,presence=1.) for q in world]

class ViewTests(unittest.TestCase):
    def test_all_15_metrics_and_form_verdicts_invariant_under_camera_yaw(self):
        _,base=landmarks(80)
        for ex in EXERCISES:
            for side in ex['modes']:
                if side=='both':continue
                reference=None
                for yaw in (0,30,60,90,-90):
                    world=rotate(base,yaw);image=project(world)
                    m,source=pose_metrics(ex['id'],side,image,640,480,world)
                    self.assertIsNotNone(m,(ex['id'],side,yaw));self.assertEqual(source,'estimated_3D')
                    verdict=geometry(ex['id'],side,image,world,m)
                    if reference:
                        for key in m:self.assertAlmostEqual(m[key],reference[0][key],places=5)
                        self.assertEqual(verdict,reference[1])
                    reference=(m,verdict)
    def test_front_view_bent_torso_uses_3d_lean(self):
        _,w=landmarks();a=math.radians(65)
        for q in w:q.y,q.z=q.y*math.cos(a)-q.z*math.sin(a),q.y*math.sin(a)+q.z*math.cos(a)
        for yaw in (0,90):
            world=rotate(w,yaw);m,_=pose_metrics('bent_row','right',project(world),640,480,world)
            self.assertAlmostEqual(m['lean'],65);self.assertTrue(MotionCoach('bent_row',server.SETTINGS).posture_ready(m))
    def test_projected_short_arm_can_use_valid_world_but_missing_world_cannot(self):
        image,w=landmarks(90);image[14].x=image[12].x;image[14].y=image[12].y
        self.assertIsNotNone(pose_metrics('front_raise','right',image,640,480,w)[0])
        self.assertIsNone(pose_metrics('front_raise','right',image,640,480,None)[0])
        w[14]=copy.deepcopy(w[12]);self.assertIsNone(pose_metrics('front_raise','right',image,640,480,w)[0])
    def test_thresholds_never_overlap_and_jitter_not_counted(self):
        for ex in EXERCISES:
            for tol in range(5,51,5):
                lim=thresholds(ex['id'],tol);self.assertGreaterEqual(abs(lim['end']-lim['start']),20)
                c=FormCoach(dict(server.SETTINGS,curl_target_deg=100),tol) if ex['family']=='curl' else MotionCoach(ex['id'],server.SETTINGS,tol)
                if ex['family']=='curl':self.assertGreaterEqual(c.down-c.up,25)
                else:
                    m=dict(elbow=10 if ex['family']=='raise' else 90 if lim['increasing'] else 175,lean=65 if ex['family']=='row' else 90 if ex['family'] in ('chest_press','triceps') else 50 if ex['family']=='incline_press' else 0,arm=90 if ex['family']=='shoulder_press' else 10,joint_elbow=170,knee=170)
                    for t in range(0,4000,100):c.update(dict(m,elbow=m['elbow']+(t%200)/100),t)
                    self.assertEqual(c.counter.reps,0)
    def test_shoulder_press_thigh_setup_does_not_award_preparation(self):
        c=MotionCoach('shoulder_press',server.SETTINGS,50)
        def m(angle,arm):return dict(elbow=angle,lean=0,arm=arm,joint_elbow=angle,knee=180)
        for t in range(0,2401,100):c.update(m(170,5),t)
        self.assertIsNotNone(c.baseline);self.assertEqual(c.counter.reps,0)
        for t in range(2500,3001,100):c.update(m(90,80),t)
        self.assertEqual(c.counter.reps,0)
        for t in range(3100,3601,100):c.update(m(170,170),t)
        for t in range(3700,4201,100):c.update(m(90,80),t)
        self.assertEqual(c.counter.reps,1)

class MultiViewRounds(unittest.TestCase):
    setUp=fixtures.RouteTests.setUp
    def test_pushups_front_and_side_count_and_reject_sag(self):
        for yaw in (0,45,90,-90):
            for tol in (10,50):
                now=[0.];r=PushUpRound(self.store,self.pa,'pushup',clock=lambda:now[0],tolerance=tol)
                def hold(down=False,bad=False,missing=False):
                    w=[P(x=0.,y=0.,z=0.) for _ in range(33)]
                    for off,z in [(0,.2),(1,-.2)]:
                        for i,x,y in [(11,0.,0.),(13,.3 if down else 0.,0. if down else .3),(15,.3 if down else 0.,.3 if down else .6),(23,.6,.6 if bad else 0.),(25,.9,0.),(27,1.2,0.)]:w[i+off]=P(x=x,y=y,z=z)
                    w=rotate(w,yaw);image=project(w)
                    if missing:image[15].visibility=image[16].visibility=0
                    for _ in range(2):now[0]+=.08;r.update(image,world=w)
                hold();self.assertIsNotNone(r.start_at);now[0]=r.start_at;hold();hold(True);hold();self.assertEqual(r.reps,1,(yaw,tol,r.cue))
                hold(True,bad=True);hold();self.assertEqual(r.reps,1)
                hold(True);hold(missing=True);hold();self.assertEqual(r.reps,1)
    def test_jumping_jacks_front_and_side_world_geometry(self):
        for yaw in (0,90,-90):
            now=[0.];r=JumpingJackRound(self.store,self.pa,'full',clock=lambda:now[0])
            def hold(up=False,hidden=False):
                w=pose(up,hidden=hidden)
                for q in w:q.x-=.5;q.z=0.
                w=rotate(w,yaw);image=project(w)
                if hidden:image[15].visibility=0.
                for _ in range(2):now[0]+=.08;r.update(image,world=w)
            hold();now[0]=r.start_at;hold();hold(True);hold();self.assertEqual(r.reps,1,(yaw,r.cue))
            hold(True);hold(hidden=True);hold();self.assertEqual(r.reps,1)
    def test_all_exercises_and_cardio_accept_50_but_reject_51(self):
        self.grant()
        for ex in EXERCISES:
            for tol,expected in [(50,200),(51,400)]:
                r=self.a.post('/start',json=dict(profile_id=self.pa,exercise=ex['id'],arm=ex['default_arm'],tolerance=tol))
                self.assertEqual(r.status_code,expected,(ex['id'],r.json));self.a.post('/stop')
        for mode in ('pushup','full','upper'):
            for tol,expected in [(50,200),(51,400),(True,400)]:
                r=self.a.post('/cardio/start',json=dict(profile_id=self.pa,mode=mode,tolerance=tol))
                self.assertEqual(r.status_code,expected,r.json);self.a.post('/stop')
    def test_cardio_saved_allowance_and_separate_rankings(self):
        from cardio import history,ranking
        now=[0.];r=PushUpRound(self.store,self.pa,'pushup',clock=lambda:now[0],tolerance=50)
        r.start_at=0.;r.reps=2;now[0]=16;r.snapshot()
        self.assertEqual(history(self.store,self.pa)[0]['tolerance'],50)
        self.assertEqual(ranking(self.store,'pushup',10),[])
        self.assertEqual(ranking(self.store,'pushup',50)[0]['best'],2)
        response=self.a.get('/cardio/leaderboard?mode=pushup&tolerance=50')
        self.assertEqual(response.status_code,200);self.assertEqual(response.json['players'][0]['best'],2)
        self.assertEqual(self.a.get('/cardio/leaderboard?mode=pushup&tolerance=51').status_code,400)
    grant=fixtures.RouteTests.grant

if __name__=='__main__':unittest.main()
