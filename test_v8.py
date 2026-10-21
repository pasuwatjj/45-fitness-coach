import json, tempfile, unittest, re
from pathlib import Path
from datetime import date
from unittest.mock import patch
from form_rules import FormCoach
from app import SETTINGS, BrowserCoach
from grip import GripCoach
from leaderboard import LeaderboardStore
from exercises import EXERCISES
from voice import PHRASES, VoiceCache

class V8(unittest.TestCase):
    def test_landmarks_response_and_legacy_jpeg(self):
        import numpy as np
        from test_sessions import FakeDetector
        with tempfile.TemporaryDirectory() as d:
            store=LeaderboardStore(Path(d)/'db');p=store.create_profile('Frames')
            coach=BrowserCoach(store);coach.grip_enabled=False
            with patch('app.vision.PoseLandmarker.create_from_options',return_value=FakeDetector()):
                coach.start('right',0,10,profile=p)
                try:
                    frame=np.zeros((240,320,3),dtype=np.uint8)
                    result=coach.accept_frame(frame,coach.state['set_id'],True)
                    self.assertEqual(result['landmarks'],[])
                    self.assertEqual(result['state']['curl_target'],80)
                    self.assertTrue(result['state']['running'])
                    self.assertTrue(coach.accept_frame(frame,coach.state['set_id']).startswith(b'\xff\xd8'))
                    with self.assertRaises(ValueError):coach.accept_frame(frame,'stale-set',True)
                finally:coach.stop()

    def test_explicit_count_target_and_margin(self):
        f=FormCoach(dict(SETTINGS,curl_target_deg=80),10)
        self.assertEqual(f.up,90)
        stricter=FormCoach(dict(SETTINGS,curl_target_deg=60),10)
        self.assertEqual(stricter.up,70)
        self.assertEqual(stricter.preferred_up,f.preferred_up)

    def test_grip_wrong_requires_hold_and_unknown_never_verified(self):
        g=GripCoach();wrong=dict(kind='curl_plane',angle=0,wrist=175)
        self.assertFalse(g.update('right','hammer_curl',wrong,0)['blocked'])
        self.assertFalse(g.update('right','hammer_curl',wrong,800)['blocked'])
        self.assertTrue(g.update('right','hammer_curl',wrong,901)['blocked'])
        unknown=g.update('right','hammer_curl',dict(kind='unknown',angle=None,wrist=None),1000)
        self.assertFalse(unknown['verified']);self.assertEqual(unknown['checks'][0]['status'],'unknown')
        correct=g.update('right','hammer_curl',dict(kind='neutral_plane',angle=90,wrist=175),1100)
        self.assertTrue(correct['verified']);self.assertFalse(correct['blocked'])
        self.assertFalse(g.update('left','curl',wrong,1100)['blocked'])

    def test_wrist_hold_independent_of_grip(self):
        g=GripCoach();r=dict(kind='unknown',angle=None,wrist=110)
        g.update('right','curl',r,0)
        out=g.update('right','curl',r,1000)
        self.assertIn('wrist',[f['code'] for f in out['feedback']]);self.assertFalse(out['blocked'])

    def test_streak_leaderboard_rest_and_missed_days_and_privacy(self):
        with tempfile.TemporaryDirectory() as d:
            store=LeaderboardStore(Path(d)/'db');a=store.create_profile('A');b=store.create_profile('B')
            for p,days in [(a,[1,2]),(b,[1])]:
                for day in days:
                    when=date(2026,10,day)
                    with patch('planner.today_thailand',return_value=when):
                        store.save_plan_day(p['id'],when.isoformat(),[dict(exercise='curl',arm_mode='right',target_sets=1,target_reps=1)])
                        plan=store.next_plan(p['id']);store.save_set(str(p['id'])+str(day),p['id'],'curl','right',1,0,0,1,{},plan=plan)
            with patch('planner.today_thailand',return_value=date(2026,10,3)):
                store.save_plan_day(a['id'],'2026-10-03',[])
                store.save_plan_day(b['id'],'2026-10-03',[dict(exercise='curl',arm_mode='right',target_sets=1,target_reps=1)])
            with patch('planner.today_thailand',return_value=date(2026,10,4)):
                rows=store.streak_standings();self.assertEqual([(x['name'],x['current']) for x in rows],[('A',2),('B',0)])
                self.assertNotIn('email',json.dumps(rows));self.assertNotIn('weight',json.dumps(rows))

    def test_all_guides_exist_and_every_teaching_phrase_has_english(self):
        root=Path(__file__).parent
        for ex in EXERCISES:
            self.assertGreaterEqual(len(ex['images']),2)
            for image in ex['images']:self.assertTrue((root/image.lstrip('/')).is_file(),image)
            for prefix in ('teach_','en__teach_'):self.assertIn(prefix+ex['id'],PHRASES)
        for k,v in PHRASES.items():
            if k.startswith('en__'):self.assertFalse(re.search('[ก-๙]',v),k)

    def test_browser_defaults_upper_body_and_personal_target(self):
        with tempfile.TemporaryDirectory() as d:
            store=LeaderboardStore(Path(d)/'db');p=store.create_profile('A');coach=BrowserCoach(store)
            with patch('app.vision.PoseLandmarker.create_from_options'):
                coach.start('right',0,10,profile=p)
                self.assertEqual(coach.focus,'upper');self.assertEqual(coach.forms['right'].up,90)
                coach.stop()

if __name__=='__main__':unittest.main()
