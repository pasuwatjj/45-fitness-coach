"""Synthetic logic/ownership regressions, not physical-camera accuracy validation."""
import math,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import numpy as np
import app as server
from leaderboard import LeaderboardStore
from strict_form import geometry,AttemptGate
import rewards
from sessions import SessionRegistry
from test_sessions import authorize_client


def landmarks(angle=160,path='front'):
    w=[NS(x=0.,y=0.,z=0.,visibility=1.) for _ in range(33)]
    for o,x in [(0,.2),(1,-.2)]:
        for i,y in [(11,0.),(13,.3),(23,.6),(25,.95),(27,1.3)]:w[i+o]=NS(x=x,y=y,z=0.,visibility=1.)
        a=math.radians(angle);dy=-.3*math.cos(a);d=.3*math.sin(a)
        w[15+o]=NS(x=x+(d if path=='side' else 0),y=.3+dy,z=d if path=='back' else -d if path=='front' else 0.,visibility=1.)
    p=[NS(x=.5+q.x*.6-q.z*.3,y=.2+q.y*.5,z=q.z,visibility=1.,presence=1.) for q in w]
    return p,w

class DirectionTests(unittest.TestCase):
    def test_curl_plane_and_unknown(self):
        for exercise in ['curl','hammer_curl']:
            for direction in ['front','side','back']:
                p,w=landmarks(80,direction);known,bad=geometry(exercise,'right',p,w,{'lean':0})
                self.assertTrue(known);self.assertEqual('curl_path' in bad,direction!='front')
            p[11].visibility=.2;self.assertFalse(geometry(exercise,'right',p,w,{'lean':0})[0])
    def test_gate_jitter_fault_and_missing(self):
        g=AttemptGate();g.observe(True,['curl_path'],0,True);g.observe(True,[],50,True)
        self.assertEqual(g.finish()[0],'accepted')
        g.observe(True,['curl_path'],100,True);g.observe(True,['curl_path'],300,True)
        self.assertEqual(g.finish()[0],'rejected')
        g.observe(False,[],400,True);self.assertEqual(g.finish()[0],'unverified')
    def test_raise_direction_is_exercise_specific(self):
        p,w=landmarks();w[14]=NS(x=-.2,y=0.,z=-.3);w[16]=NS(x=-.2,y=0.,z=-.6)
        self.assertNotIn('raise_path',geometry('front_raise','right',p,w,{'lean':0})[1])
        self.assertIn('raise_path',geometry('lateral_raise','right',p,w,{'lean':0})[1])

class FullAttemptTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=LeaderboardStore(Path(self.tmp.name)/'db');self.profile=self.store.create_profile('Player')
        self.c=server.BrowserCoach(self.store);self.c.configure('right',5,'upper','curl')
        self.c.state.update(running=True,paused=False,profile=self.profile)
        self.now=int(time.monotonic()*1000);self.frame=np.zeros((720,960,3),dtype=np.uint8)
        self.feed(160,2500);self.assertTrue(self.c.state['calibrated'])
    def feed(self,angle,hold=200,path='front',known=True):
        p,w=landmarks(angle,path)
        for _ in range(max(1,hold//50)):
            self.now+=50
            self.c.process(self.frame,NS(pose_landmarks=[p],pose_world_landmarks=[w] if known else []),self.now)
    def cycle(self,path='front'):
        for angle in [140,120,100,80,60,60,80,100,120,140,160,160]:self.feed(angle,path=path)
    def test_wrong_red_attempt_not_saved_to_scores_or_coins_then_recovery(self):
        self.cycle('side');self.assertEqual(self.c.state['reps'],0);self.assertEqual(self.c.rejected,1)
        self.assertEqual(self.c.rep_events[-1]['result'],'rejected')
        self.c.pause();self.assertEqual(self.store.standings('curl','right'),[])
        self.assertEqual(rewards.overview(self.store,self.profile['id'])['coins'],0)
        from profile_data import overview
        self.assertEqual(overview(self.store,self.profile['id'])['sets'][0]['rejected'],1)
        self.c.new_set();self.feed(160,250);self.cycle()
        self.assertEqual(self.c.state['reps'],1);self.c.pause();self.c.pause()
        self.assertEqual(rewards.overview(self.store,self.profile['id'])['coins'],1)
    def test_wrong_cycle_cannot_complete_daily_plan(self):
        day=server.today_thailand().isoformat()
        self.store.save_plan_day(self.profile['id'],day,[dict(exercise='curl',arm_mode='right',target_sets=1,target_reps=1)])
        self.c.state['plan']=self.store.next_plan(self.profile['id'])
        self.cycle('back');self.c.pause()
        self.assertFalse(self.store.plan_day(self.profile['id'])['complete'])
        self.assertEqual(rewards.overview(self.store,self.profile['id'])['available_fire'],0)
        self.c.new_set();self.feed(160,250);self.cycle()
        self.assertTrue(self.store.plan_day(self.profile['id'])['complete'])
        for _ in range(2):self.assertEqual(rewards.claim_fire(self.store,self.profile['id'])['coins'],11)
        self.assertEqual(self.store.plan_month(self.profile['id'],day[:7])['streak']['current'],1)
    def test_two_arms_need_two_accepted_sides(self):
        self.c.configure('both',5,'upper','curl');self.feed(160,2500)
        for angle in [140,120,100,80,60,60,80,100,120,140,160,160]:
            p,w=landmarks(angle,'front');badp,badw=landmarks(angle,'side')
            p[16]=badp[16];w[16]=badw[16]
            for _ in range(4):
                self.now+=50;self.c.process(self.frame,NS(pose_landmarks=[p],pose_world_landmarks=[w]),self.now)
        self.assertEqual(self.c.forms['left'].counter.reps,1)
        self.assertEqual(self.c.forms['right'].counter.reps,0)
        self.assertEqual(self.c.state['reps'],0);self.c.pause()
        self.assertEqual(rewards.overview(self.store,self.profile['id'])['coins'],0)
        from profile_data import overview
        self.assertEqual(overview(self.store,self.profile['id'])['sets'][0]['accepted'],1)
    def test_valid_fast_cycle_still_counts(self):
        for angle in [140,110,70,60,90,120,150,160]:self.feed(angle,100)
        self.assertEqual(self.c.state['reps'],1);self.assertEqual(self.c.rep_events[-1]['result'],'accepted')
    def test_wrong_grip_rejects_completed_motion(self):
        self.c.grip_results={'right':{'blocked':True,'feedback':[]}}
        self.cycle();self.assertEqual(self.c.state['reps'],0)
        self.assertIn('grip',self.c.rep_events[-1]['reasons'])
    def test_unknown_world_does_not_award(self):
        # A source change recalibrates; no 3D evidence is not a red error.
        self.feed(160,2600,known=False)
        for angle in [140,120,100,80,60,60,80,100,120,140,160,160]:self.feed(angle,known=False)
        self.assertEqual(self.c.state['reps'],0)
        self.assertTrue(all(e['result']!='accepted' for e in self.c.rep_events))

class RewardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=LeaderboardStore(Path(self.tmp.name)/'db');self.p=self.store.create_profile('One')['id'];self.q=self.store.create_profile('Two')['id']
    def test_save_redeem_deduplicate_and_insufficient(self):
        self.store.save_set('set1',self.p,'curl','right',40,0,0,40,{})
        for _ in range(2):rewards.save_quality(self.store,'set1',self.p,'curl','right',999,3,1)
        self.assertEqual(rewards.overview(self.store,self.p)['coins'],40)
        for _ in range(2):d=rewards.redeem(self.store,self.p,'spark')
        self.assertEqual(d['coins'],10);self.assertEqual(d['unlocked'],['spark'])
        with self.assertRaises(ValueError):rewards.redeem(self.store,self.p,'star')
        self.assertEqual(rewards.overview(self.store,self.q)['coins'],0)
    def test_completed_fire_claim_once_no_plan_mutation(self):
        with patch.object(rewards,'completed_days',return_value=['2026-10-01','2026-10-02']):
            for _ in range(2):d=rewards.claim_fire(self.store,self.p)
            self.assertEqual(d['coins'],20);self.assertEqual(d['available_fire'],0)
        self.assertEqual(rewards.overview(self.store,self.q)['coins'],0)
    def test_owner_and_no_client_coin_injection(self):
        reg=SessionRegistry(lambda:server.BrowserCoach(self.store));self.addCleanup(reg.stop_all)
        with patch.object(server,'store',self.store),patch.object(server,'sessions',reg):
            a=server.app.test_client();b=server.app.test_client();authorize_client(server,a);authorize_client(server,b)
            existing=a.get('/profiles').json['profiles']
            p=existing[0]['id'] if existing else a.post('/profiles',json={'name':'Owned'}).json['profile']['id']
            self.assertEqual(b.get(f'/profiles/{p}/rewards').status_code,404)
            self.assertEqual(b.post(f'/profiles/{p}/rewards',json={'action':'claim'}).status_code,404)
            # v12 retires legacy redemption endpoints; clients cannot mint or spend purple coins.
            self.assertEqual(a.post(f'/profiles/{p}/rewards',json={'action':'claim','coins':999}).status_code,400)
            self.assertEqual(server.app.test_client().get(f'/profiles/{p}/rewards').status_code,401)

if __name__=='__main__':unittest.main()
