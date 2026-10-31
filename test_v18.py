"""Lifecycle stress, round accounting, access control and amended-plan regression tests."""
import tempfile,time,uuid
from pathlib import Path
from types import SimpleNamespace as Point
from unittest import TestCase
from unittest.mock import patch
import unittest
import app as server
import cardio,rewards,community
from leaderboard import LeaderboardStore
from planner import today_thailand
import test_v13 as fixtures


def pose(up=False,spread=None,hidden=False):
    p=[Point(x=.5,y=.5,visibility=1) for _ in range(33)]
    for id,x,y in [(11,.35,.35),(12,.65,.35),(23,.42,.65),(24,.58,.65),
                   (13,.25,.23 if up else .5),(14,.75,.23 if up else .5),
                   (15,.2,.12 if up else .7),(16,.8,.12 if up else .7),
                   (25,.42,.8),(26,.58,.8),(27,.26 if up else .46,.95),(28,.74 if up else .54,.95)]:
        p[id]=Point(x=x,y=y,visibility=1)
    if spread is False:p[27].x=.46;p[28].x=.54
    if hidden:p[15].visibility=.1
    return p

class CardioTests(TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=LeaderboardStore(Path(self.tmp.name)/'db');self.pid=self.store.create_profile('Player')['id'];self.now=100
        self.round=cardio.JumpingJackRound(self.store,self.pid,'full',lambda:self.now)
    def hold(self,points):
        for _ in range(2):self.now+=.08;self.round.update(points)
    def ready(self):
        self.hold(pose());self.now=self.round.start_at;self.hold(pose())
    def cycle(self,spread=None):self.hold(pose(True,spread));self.hold(pose(False,spread))
    def finish(self):self.now=self.round.start_at+15;return self.round.snapshot()
    def test_full_cycle_and_exactly_once_coin_credit(self):
        self.ready()
        for _ in range(12):self.cycle()
        self.assertEqual(self.round.reps,12);self.assertEqual(rewards.overview(self.store,self.pid)['coins'],0)
        self.assertTrue(self.finish()['done']);self.round.stop();self.round.snapshot()
        self.assertEqual(rewards.overview(self.store,self.pid)['coins'],12)
        self.assertEqual(cardio.ranking(self.store,'full')[0]['best'],12)
        self.assertEqual(cardio.ranking(self.store,'upper'),[])
    def test_full_does_not_count_arms_without_spread(self):
        self.ready()
        for _ in range(5):self.cycle(False)
        self.assertEqual(self.round.reps,0)
    def test_upper_mode_counts_arms_and_separate_leaderboard(self):
        self.round.mode='upper';self.ready()
        for _ in range(5):self.cycle(False)
        self.assertEqual(self.round.reps,5);self.finish()
        self.assertEqual(cardio.ranking(self.store,'upper')[0]['best'],5)
    def test_missing_joints_and_gap_cannot_complete_stale_rep(self):
        self.ready();self.hold(pose(True));self.hold(pose(hidden=True));self.hold(pose())
        self.assertEqual(self.round.reps,0)
        self.hold(pose(True));self.now+=2;self.hold(pose())
        self.assertEqual(self.round.reps,0)
    def test_timer_starts_on_visible_pose_without_free_rep(self):
        self.hold(pose(hidden=True));self.assertIsNone(self.round.start_at)
        self.hold(pose(True));self.assertIsNotNone(self.round.start_at)
        self.assertEqual(self.round.reps,0)
        self.ready();self.assertEqual(self.round.reps,0)
    def test_cancelled_round_earns_no_coins(self):
        self.ready();self.cycle();self.round.stop();self.now+=30
        self.assertTrue(self.round.snapshot()['cancelled'])
        self.assertFalse(self.round.snapshot()['done']);self.assertEqual(rewards.overview(self.store,self.pid)['coins'],0)
    def test_frames_after_deadline_do_not_score(self):
        self.ready();self.cycle();self.finish();self.cycle();self.assertEqual(self.round.reps,1)
    def test_still_pose_and_single_frame_noise_do_not_score(self):
        self.ready()
        for _ in range(12):self.hold(pose(True))
        self.assertEqual(self.round.reps,0)
        self.now+=.08;self.round.update(pose());self.now+=.01;self.round.update(pose(True))
        self.assertEqual(self.round.reps,0)

class RouteTests(TestCase):
    setUp=fixtures.RouteTests.setUp
    def test_200_camera_cycles_reuse_detector_and_manual_reset_rebuilds(self):
        original=self.reg.items[self.ta]['coach'];other=self.reg.items[self.tb]['coach']
        detector=None
        for i in range(200):
            old=self.a.get('/status').json['set_id']
            self.assertEqual(self.a.post('/camera/recover',headers={'X-Set-ID':old}).status_code,200)
            r=self.a.post('/start',json=dict(profile_id=self.pa,exercise='curl',arm='right',grip_enabled=False))
            self.assertEqual(r.status_code,200)
            if detector is None:detector=original.detector
            self.assertIs(original.detector,detector)
            self.assertEqual(self.a.post('/stop',headers={'X-Set-ID':old}).status_code,409)
            self.assertEqual(self.a.post('/stop',headers={'X-Set-ID':r.json['state']['set_id']}).status_code,200)
        self.assertIs(self.reg.items[self.ta]['coach'],original);self.assertIs(self.reg.items[self.tb]['coach'],other)
        self.assertEqual(self.a.post('/camera/recover',json={'rebuild':True},headers={'X-Set-ID':original.state['set_id']}).status_code,200)
        self.assertIsNone(original.detector)
    def test_cardio_ownership_and_no_client_rep_credit(self):
        self.assertEqual(self.a.post('/cardio/start',json=dict(profile_id=self.pb,mode='full')).status_code,404)
        r=self.a.post('/cardio/start',json=dict(profile_id=self.pa,mode='upper',reps=99999))
        self.assertEqual(r.status_code,200);self.assertEqual(r.json['state']['cardio']['reps'],0)
        self.assertEqual(self.a.post('/cardio/start',json=dict(profile_id=self.pa,mode='full')).status_code,409)
        self.a.post('/stop');self.assertEqual(rewards.overview(self.store,self.pa)['coins'],0)
    def test_stale_start_after_reset_rejected(self):
        old=self.a.get('/status').json['set_id'];self.a.post('/camera/recover',headers={'X-Set-ID':old})
        for path in ['/start','/cardio/start']:
            self.assertEqual(self.a.post(path,headers={'X-Set-ID':old},json=dict(profile_id=self.pa)).status_code,409)
    def test_admin_total_paging_and_normal_user_denied(self):
        community.grant_admin(self.store,self.a.get('/auth/me').json['email'])
        with self.store.connect() as db:
            for i in range(52):db.execute('INSERT INTO accounts(email,password_hash) VALUES(?,?)',(f'page{i}@example.com','test-only'))
        first=self.a.get('/admin/accounts').json;second=self.a.get('/admin/accounts?page=2').json
        self.assertEqual(first['total'],54);self.assertEqual(first['pages'],2)
        self.assertEqual(len(first['accounts'])+len(second['accounts']),54)
        self.assertEqual(self.b.get('/admin/accounts?page=2').status_code,403)
    def test_profile_muscles_aggregate_all_history(self):
        for i in range(65):self.store.save_set(str(uuid.uuid4()),self.pa,'curl','right',2,0,0,2,{})
        d=self.a.get(f'/profiles/{self.pa}/overview').json
        arms=next(g for g in d['muscle_groups'] if g['group']=='arms')
        self.assertEqual(arms['sets'],65);self.assertEqual(arms['reps'],130)
    def test_adjust_remaining_preserves_credits_and_earns_fire(self):
        today=today_thailand().isoformat();item=dict(exercise='curl',arm_mode='right',target_sets=3,target_reps=2)
        self.store.save_plan_day(self.pa,today,[item]);plan=self.store.next_plan(self.pa)
        self.store.save_set('first',self.pa,'curl','right',2,0,0,2,{},plan=plan)
        replacement=dict(exercise='single_row',arm_mode='right',target_sets=1,target_reps=2)
        r=self.a.post(f'/profiles/{self.pa}/calendar/day',json=dict(date=today,items=[replacement],adjust_remaining=True))
        self.assertEqual(r.status_code,200);self.assertEqual(r.json['day']['completed_sets'],1)
        self.assertFalse(r.json['day']['complete']);plan=self.store.next_plan(self.pa)
        self.store.save_set('second',self.pa,'single_row','right',2,0,0,2,{},plan=plan)
        self.assertTrue(self.store.plan_day(self.pa)['complete'])
        self.assertEqual(self.store.plan_month(self.pa,today[:7])['streak']['current'],1)
        self.assertEqual(self.a.post(f'/profiles/{self.pa}/calendar/day',json=dict(date=today,items=[],adjust_remaining=True)).status_code,400)

if __name__=='__main__':unittest.main()
