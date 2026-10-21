"""Synthetic regressions for motion logic; not a validation of camera accuracy."""
import json
from pathlib import Path
import unittest
from types import SimpleNamespace
import tempfile
from unittest.mock import patch, ANY

from form_rules import FormCoach, measurements

SETTINGS = json.loads((Path(__file__).parent / 'settings.json').read_text())


class FormTests(unittest.TestCase):
    def setUp(self):
        self.coach = FormCoach(SETTINGS)
        self.now = 0

    def feed(self, angle, duration=100, lean=0, arm=0):
        out = None
        for _ in range(max(1, duration // 50)):
            self.now += 50
            out = self.coach.update(dict(elbow=angle, lean=lean, arm=arm), self.now)
        return out

    def calibrate(self):
        out = self.feed(160, 2300)
        self.assertTrue(out['calibrated'])
        self.feed(160, 200)

    def cycle(self, lean=0, arm=0):
        for angle in (140, 120, 100, 80, 60, 50):
            self.feed(angle, 200, lean, arm)
        self.feed(50, 200, lean, arm)
        for angle in (70, 90, 110, 130, 150, 160):
            out = self.feed(angle, 220, lean, arm)
        return out

    def test_pixel_geometry_and_degenerate_input(self):
        m = measurements((100, 100), (100, 200), (100, 300), (100, 400))
        self.assertEqual(m['elbow'], 180)
        self.assertEqual(m['lean'], 0)
        self.assertEqual(m['arm'], 0)
        self.assertIsNone(measurements((0, 0), (0, 0), (10, 0), (0, 1)))

    def test_arms_only_does_not_require_hip_or_grade_torso(self):
        m = measurements((100, 100), (100, 200), (100, 300))
        self.assertIsNone(m['lean'])
        for t in range(0, 2500, 50):
            out = self.coach.update(m, t)
        self.assertTrue(out['calibrated'])
        torso = next(c for c in out['checks'] if c['code'] == 'torso')
        self.assertEqual(torso['status'], 'unknown')

    def test_3d_elbow_angle_is_rotation_invariant(self):
        from curl_counter import elbow_angle
        self.assertAlmostEqual(elbow_angle((0,0,0), (0,1,0), (0,1,1)), 90)
        self.assertAlmostEqual(elbow_angle((0,0,0), (1,0,0), (1,1,0)), 90)

    def test_controlled_full_cycles_count_without_false_warnings(self):
        self.calibrate()
        for reps in range(1, 4):
            out = self.cycle()
            self.assertEqual(out['reps'], reps)
            self.assertEqual(out['flagged'], 0)
            self.assertEqual(out['feedback'], [])

    def test_stable_lean_and_arm_warning_and_flagged_rep(self):
        self.calibrate()
        out = self.cycle(lean=30, arm=35)
        self.assertEqual(out['reps'], 1)
        self.assertEqual(out['flagged'], 1)
        self.assertTrue({'torso', 'arm'} <= {f['code'] for f in out['feedback']})

    def test_short_noise_does_not_warn_and_recovery_clears(self):
        self.calibrate()
        self.assertFalse(self.feed(160, 150, lean=35)['feedback'])
        self.assertFalse(self.feed(160, 500)['feedback'])
        self.assertTrue(self.feed(160, 1000, lean=35)['feedback'])
        self.assertFalse(self.feed(160, 750)['feedback'])

    def test_untrusted_initial_posture_cannot_calibrate(self):
        for condition in ({'lean': 35}, {'arm': 40}, {}):
            c = FormCoach(SETTINGS)
            for t in range(0, 3000, 50):
                out = c.update(dict(elbow=100 if not condition else 160,
                                    lean=condition.get('lean', 0), arm=condition.get('arm', 0)), t)
            self.assertFalse(out['calibrated'])
            self.assertEqual(out['reps'], 0)

    def test_pose_loss_cancels_unfinished_cycle_and_requires_recalibration(self):
        self.calibrate()
        self.feed(100, 800)
        self.feed(50, 500)
        self.assertEqual(self.coach.counter.phase, 'raised')
        out = self.coach.unavailable(self.now + 50, 'lost')
        self.assertEqual(out['form_level'], 'unknown')
        self.assertEqual(self.feed(160, 300)['reps'], 0)
        self.coach.unavailable(self.now, 'lost')
        out = self.coach.unavailable(self.now + 1600, 'lost')
        self.assertFalse(out['calibrated'])

    def test_partial_tips_deferred_until_repeated_substantial_attempts(self):
        self.calibrate()
        self.feed(110, 600)
        out = self.feed(140, 200)
        self.assertEqual(out['reps'], 0)
        self.assertNotIn('flexion', {f['code'] for f in out['feedback']})
        self.assertEqual(out['observations']['flexion'], 1)
        self.feed(160, 600)
        self.feed(110, 600)
        out = self.feed(140, 200)
        self.assertIn('flexion', {f['code'] for f in out['feedback']})
        # Fresh session: reach the top, then reverse before extension.
        self.setUp()
        self.calibrate()
        self.feed(100, 900)
        self.feed(50, 400)
        self.feed(110, 900)
        out = self.feed(80, 200)
        self.assertEqual(out['reps'], 0)
        self.assertNotIn('extension', {f['code'] for f in out['feedback']})
        self.feed(50, 500)
        self.feed(110, 900)
        out = self.feed(80, 200)
        self.assertIn('extension', {f['code'] for f in out['feedback']})

    def test_fast_full_cycle_has_tempo_hint(self):
        self.calibrate()
        self.feed(120, 50)
        self.feed(50, 200)
        self.feed(90, 50)
        out = self.feed(160, 350)
        self.assertEqual(out['reps'], 1)
        self.assertEqual(out['flagged'], 1)
        self.assertIn('tempo', {f['code'] for f in out['feedback']})

    def test_tolerance_is_applied_to_endpoints_and_warnings(self):
        for tol in (5, 10, 15):
            c = FormCoach(SETTINGS, tol)
            self.assertEqual(c.down, 160-tol-20)
            self.assertEqual(c.up, min(100,50+tol+35))
            self.assertEqual(c.lean_limit, 8+tol)

    def test_reset_and_recalibrate_keep_distinct_contracts(self):
        self.calibrate()
        self.cycle()
        self.coach.recalibrate()
        self.assertEqual(self.coach.counter.reps, 1)
        self.assertIsNone(self.coach.baseline)
        self.coach.reset()
        self.assertEqual(self.coach.counter.reps, 0)
        self.assertEqual(self.coach.flagged, 0)


class WebTests(unittest.TestCase):
    def setUp(self):
        import app
        self.app_module = app
        from leaderboard import LeaderboardStore
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.scoreboard = LeaderboardStore(Path(folder.name)/'scores.db')
        p = patch.object(app, 'store', self.scoreboard)
        p.start()
        self.addCleanup(p.stop)
        self.client = app.app.test_client()
        from test_sessions import authorize_client
        token=authorize_client(app,self.client)
        self.private_coach=app.sessions.items[token]['coach']
        self.profile=self.client.post('/profiles',json={'name':'Route tester'}).json['profile']

    def test_page_and_status_contract(self):
        page = self.client.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'goblet_squat', page.data)
        self.assertIn(b'calendarPage', page.data)
        status = self.client.get('/status').json
        for key in ('feedback', 'checks', 'flagged', 'thresholds', 'calibrated'):
            self.assertIn(key, status)

    def test_placeholder_and_invalid_settings_rejected(self):
        for body in ({'exercise': 'exercise2'}, {'tolerance': 100},
                     {'tolerance': True}, {'camera': -1}, {'arm': 'all'}, [1]):
            self.assertEqual(self.client.post('/start', json=body).status_code, 400)

    def test_valid_request_forwards_config(self):
        from unittest.mock import patch
        with patch.object(self.private_coach, 'start', return_value=True) as start:
            self.assertEqual(self.client.post('/start', json={'arm':'left', 'camera':1,
                              'exercise':'curl', 'tolerance':15,'profile_id':self.profile['id']}).status_code, 200)
            start.assert_called_once_with('left', 1, 15, 'arms', ANY)

    def test_missing_joints_gives_unknown_and_draw_does_not_crash(self):
        import numpy as np
        c = self.app_module.CameraCoach()
        frame = np.zeros((720, 960, 3), dtype=np.uint8)
        p = [SimpleNamespace(x=.4, y=.4, visibility=0, presence=0) for _ in range(33)]
        c.process(frame, SimpleNamespace(pose_landmarks=[p]), (12,14,16), 0)
        self.assertIsNone(c.snapshot()['angle'])
        self.assertEqual(c.snapshot()['form_level'], 'unknown')

    def test_both_arm_selection_and_focus_forwarded(self):
        from unittest.mock import patch
        with patch.object(self.private_coach, 'start', return_value=True) as start:
            self.assertEqual(self.client.post('/start', json={'arm':'both',
                             'focus':'upper','profile_id':self.profile['id']}).status_code, 200)
            start.assert_called_once_with('both', 0, 10, 'upper', ANY)

    def test_lan_access_key_and_cross_origin_control(self):
        app = self.app_module
        remote = app.app.test_client()
        self.assertEqual(remote.get('/status', environ_overrides={'REMOTE_ADDR':'192.168.1.2'}).status_code, 403)
        response = remote.get('/45-fitness-coach?key='+app.ACCESS_KEY,
                              environ_overrides={'REMOTE_ADDR':'192.168.1.2'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(remote.get('/status', environ_overrides={'REMOTE_ADDR':'192.168.1.2'}).status_code, 200)
        self.assertEqual(self.client.post('/reset', headers={'Origin':'https://other.example'}).status_code, 403)

    def test_phone_link_qr_encodes_round_trip(self):
        from unittest.mock import patch
        import cv2, numpy as np
        with patch.object(self.app_module, 'lan_addresses', return_value=['192.168.1.25']):
            link = self.client.get('/connection').json['links'][0]['url']
            qr = self.client.get('/connection-qr/0')
            self.assertEqual(qr.status_code, 200)
            decoded = cv2.QRCodeDetector().detectAndDecode(cv2.imdecode(np.frombuffer(qr.data, np.uint8), cv2.IMREAD_GRAYSCALE))[0]
            self.assertEqual(decoded, link)


class BilateralTests(unittest.TestCase):
    def setUp(self):
        import app, numpy as np
        self.app = app
        self.coach = app.CameraCoach()
        self.coach.configure('both', 10, 'arms')
        self.frame = np.zeros((720,960,3), dtype=np.uint8)
        self.now = 0

    def frame_at(self, left, right, duration=200, lost_left=False):
        import math
        for _ in range(duration//50):
            self.now += 50
            points = [SimpleNamespace(x=.5,y=.5,visibility=0,presence=0) for _ in range(33)]
            for arm, angle in [('left', left), ('right', right)]:
                shoulder, elbow, wrist = self.app.ARM_IDS[arm]
                x = .25 if arm == 'left' else .7
                for i, px, py in [(shoulder,x,.2),(elbow,x,.4),
                    (wrist,x+math.sin(math.radians(angle))*144/960,.4-math.cos(math.radians(angle))*.2)]:
                    points[i] = SimpleNamespace(x=px,y=py,visibility=0 if arm=='left' and lost_left else 1,presence=1)
            self.coach.process(self.frame.copy(), SimpleNamespace(pose_landmarks=[points]), self.now)
        return self.coach.snapshot()

    def test_two_arms_count_as_one_pair_and_missing_arm_is_independent(self):
        self.frame_at(160,160,2500)
        for angle in (140,120,100,80,60,50,50,70,90,110,130,150,160):
            out = self.frame_at(angle,angle,250)
        self.assertEqual(out['arms']['left']['reps'],1)
        self.assertEqual(out['arms']['right']['reps'],1)
        self.assertEqual(out['reps'],1)
        for angle in (140,120,100,80,60,50,50,70,90,110,130,150,160):
            out = self.frame_at(160,angle,250,lost_left=True)
        self.assertEqual(out['arms']['left']['reps'],1)
        self.assertEqual(out['arms']['right']['reps'],2)
        self.assertEqual(out['reps'],1)
        self.assertEqual(out['form_level'],'unknown')

    def test_reset_both_counts_and_single_selection_ignores_other_arm(self):
        self.coach.configure('right',10,'arms')
        self.frame_at(160,160,2500,lost_left=True)
        for angle in (140,120,100,80,60,50,50,70,90,110,130,150,160):
            out = self.frame_at(160,angle,250,lost_left=True)
        self.assertEqual(out['reps'],1)
        self.assertNotIn('left',out['arms'])
        self.coach.reset()
        self.assertEqual(self.coach.snapshot()['reps'],0)


if __name__ == '__main__':
    unittest.main()
