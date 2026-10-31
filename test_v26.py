"""v26 synthetic and API regressions. Does not certify physical-camera accuracy."""
import json,tempfile,time,uuid,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from types import SimpleNamespace as NS
import numpy as np
import app as server
import rewards
import character,training_economy as economy,training_modes,shop,membership
from leaderboard import LeaderboardStore
import test_v13 as fixtures
from test_v11 import landmarks

class ModeAndArmTests(unittest.TestCase):
    def test_every_exercise_has_progressively_tighter_endpoints(self):
        from form_rules import FormCoach
        from motion_coach import MotionCoach
        for ex in server.CATALOG:
            out=[]
            for level in training_modes.LEVELS:
                cfg,t=training_modes.options(ex,level,10,server.SETTINGS)
                form=FormCoach(cfg,t) if server.CATALOG[ex]['family']=='curl' else MotionCoach(ex,cfg,t)
                out.append((form.down,form.up) if server.CATALOG[ex]['family']=='curl' else (form.limits['start'],form.limits['end']))
            self.assertNotEqual(out[0],out[1],ex);self.assertNotEqual(out[1],out[2],ex)
    def test_hysteresis_no_oscillation_and_arm_only_visibility(self):
        p,_=landmarks();p[23].visibility=p[24].visibility=0
        a=training_modes.ArmSelector()
        for now in range(0,2000,50):self.assertEqual(a.choose(p,now),('right',False))
        p[14].visibility=0
        self.assertEqual(a.choose(p,2000),('right',False))
        self.assertEqual(a.choose(p,2200),('right',False))
        self.assertEqual(a.choose(p,2450),('left',True))
        p[14].visibility=1
        for now in range(2500,4000,50):self.assertEqual(a.choose(p,now),('left',False))
        for i in range(20):
            p[13].visibility=0 if i%2 else 1
            self.assertEqual(a.choose(p,4000+i*100)[0],'left')
    def test_auto_switch_saves_each_side_and_never_completes_interrupted_rep(self):
        with tempfile.TemporaryDirectory() as d:
            store=LeaderboardStore(Path(d)/'db');profile=store.create_profile('Auto')
            c=server.BrowserCoach(store);c.requested_auto_arm=True;c.configure('right',10,'upper','curl');c.state.update(running=True,paused=False,profile=profile)
            frame=np.zeros((720,960,3),dtype=np.uint8);now=100000
            def feed(angle=160,side='right',hold=200):
                nonlocal now
                p,w=landmarks(angle)
                # Keep shoulders/hips visible for geometry, obscure only other wrist.
                p[15 if side=='right' else 16].visibility=.1
                for _ in range(hold//50):
                    now+=50;c.process(frame,NS(pose_landmarks=[p],pose_world_landmarks=[w]),now)
            def cycle(side):
                for angle in [140,120,100,80,60,60,80,100,120,140,160,160]:feed(angle,side)
            feed(160,'right',2500);cycle('right');self.assertEqual(c.state['reps'],1)
            feed(60,'right',300) # unfinished motion is discarded when side changes
            feed(160,'left',3000);self.assertEqual(c.auto_side,'left');self.assertEqual(c.state['reps'],1)
            cycle('left');self.assertEqual(c.state['reps'],2)
            original=c.forms['right'].baseline
            feed(160,'right',650);self.assertEqual(c.auto_side,'right');self.assertIs(c.forms['right'].baseline,original);self.assertTrue(c.state['calibrated']);self.assertEqual(c.state['reps'],2)
            cycle('right');self.assertEqual(c.state['reps'],3)
            c.pause();c.pause()
            with store.connect() as db:
                row=db.execute('SELECT * FROM workout_sets').fetchone();self.assertEqual((row['arm_mode'],row['reps'],row['left_reps'],row['right_reps']),('auto',3,1,2))
                economy.schema(db);self.assertEqual(economy.balance(db,profile['id'])['beginner'],3)

class EconomyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=LeaderboardStore(Path(self.tmp.name)/'db');self.p=self.store.create_profile('Owner')['id'];self.q=self.store.create_profile('Other')['id'];self.owner='account:1'
        from accounts import schema
        schema(self.store)
        with self.store.connect() as db:
            shop.schema(db);economy.schema(db)
            db.execute('CREATE TABLE IF NOT EXISTS profile_owners(profile_id INTEGER PRIMARY KEY,owner TEXT NOT NULL)')
            db.execute('INSERT INTO profile_owners VALUES(?,?)',(self.p,self.owner));db.execute('INSERT INTO profile_owners VALUES(?,?)',(self.q,'account:2'))
            db.execute("INSERT INTO reward_ledger(id,profile_id,amount,kind) VALUES('oldgold',?,123,'workout')",(self.p,))
    def fund(self,currency,n):
        with self.store.connect() as db:db.execute('INSERT INTO training_ledger VALUES(?,?,?,?,?,?)',(str(uuid.uuid4()),self.p,currency,n,'test',time.time()))
    def act(self,**kw):return economy.act(self.store,self.owner,self.p,dict(request_id=str(uuid.uuid4()),**kw))
    def vip(self):
        with self.store.connect() as db:db.execute('INSERT OR REPLACE INTO vip_memberships VALUES(?,?)',(self.owner,time.time()+1000))
    def order(self,key=None):return economy.act(self.store,self.owner,self.p,dict(request_id=key or str(uuid.uuid4()),action='redeem',name='Test',phone='0800000000',address='Test address'))
    def test_each_exchange_rate_available_without_vip_and_legacy_unchanged(self):
        for key,n in economy.RATES.items():
            self.fund(key,n);self.act(action='exchange',currency=key,quantity=1)
        d=shop.overview(self.store,self.owner,self.p);self.assertEqual(d['wallet'],dict(beginner=0,pro=0,expert=0,universal=3));self.assertEqual(d['gold'],123);self.assertEqual(d['purple'],0)
    def test_idempotent_replay_signature_and_cross_owner_protection(self):
        self.fund('expert',30);data=dict(action='exchange',currency='expert',quantity=1,request_id=str(uuid.uuid4()))
        for _ in range(3):economy.act(self.store,self.owner,self.p,data)
        self.assertEqual(economy.overview(self.store,self.owner,self.p)['wallet']['expert'],20)
        with self.assertRaises(ValueError):economy.act(self.store,self.owner,self.p,dict(data,quantity=2))
        with self.assertRaises(PermissionError):economy.act(self.store,'account:2',self.p,data)
        with self.assertRaises(ValueError):economy.act(self.store,'account:2',self.q,data)
        for bad in [0,-1,True,1.5,101,'1']:
            with self.assertRaises(ValueError):self.act(action='exchange',currency='expert',quantity=bad)
    def test_concurrent_spending_and_duplicate_request_across_connections(self):
        self.fund('expert',10)
        def spend(_):
            try:return economy.act(LeaderboardStore(self.store.path),self.owner,self.p,dict(action='exchange',currency='expert',quantity=1,request_id=str(uuid.uuid4()))) is not None
            except ValueError:return False
        with ThreadPoolExecutor(max_workers=6) as pool:self.assertEqual(sum(pool.map(spend,range(6))),1)
        self.fund('expert',10);key=str(uuid.uuid4())
        def replay(_):return economy.act(LeaderboardStore(self.store.path),self.owner,self.p,dict(action='exchange',currency='expert',request_id=key))
        with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(replay,range(6)))
        self.assertEqual(economy.overview(self.store,self.owner,self.p)['wallet']['universal'],2)
    def test_vip_reward_and_refund_original_currency_exactly_once(self):
        self.fund('universal',100)
        with self.assertRaises(PermissionError):self.order()
        self.vip();key=str(uuid.uuid4());self.order(key);self.order(key)
        self.assertEqual(economy.overview(self.store,self.owner,self.p)['wallet']['universal'],0)
        with self.store.connect() as db:db.execute('UPDATE vip_memberships SET expires=0')
        with self.assertRaises(ValueError):shop.resolve(self.store,key,'cancelled','account:2')
        for _ in range(2):shop.resolve(self.store,key,'cancelled',self.owner)
        d=shop.overview(self.store,self.owner,self.p);self.assertEqual(d['wallet']['universal'],100);self.assertEqual(d['purple'],0);self.assertEqual(d['orders'][0]['charge_currency'],'universal')
    def test_fulfilled_cannot_refund(self):
        self.fund('universal',100);self.vip();key=str(uuid.uuid4());self.order(key);shop.resolve(self.store,key,'fulfilled')
        with self.assertRaises(ValueError):shop.resolve(self.store,key,'cancelled',self.owner)
    def test_workout_coin_insert_is_atomic_and_immutable(self):
        with patch('training_economy.credit_db',side_effect=ValueError('injected storage failure')):
            with self.assertRaises(ValueError):self.store.save_set('atomic',self.p,'curl','auto',3,0,1,2,{},difficulty='pro')
        with self.store.connect() as db:self.assertIsNone(db.execute("SELECT * FROM workout_sets WHERE id='atomic'").fetchone())
        for _ in range(3):self.store.save_set('atomic',self.p,'curl','auto',3,0,1,2,{},difficulty='pro')
        with self.assertRaises(ValueError):self.store.save_set('atomic',self.p,'curl','auto',3,0,1,2,{},difficulty='expert')
        fresh=LeaderboardStore(self.store.path);self.assertEqual(economy.overview(fresh,self.owner,self.p)['wallet']['pro'],3)

class ApiAndCharacterTests(unittest.TestCase):
    setUp=fixtures.RouteTests.setUp
    def start(self,**kwargs):return self.a.post('/start',json=dict(profile_id=self.pa,exercise='curl',arm='right',**kwargs))
    def test_level_frozen_session_private_and_toggle_saves_side(self):
        self.assertEqual(self.start(difficulty='pro',auto_arm=True).status_code,200);c=self.reg.items[self.ta]['coach'];sid=c.state['set_id']
        self.assertEqual(self.start(difficulty='expert').status_code,409);self.assertEqual(c.difficulty,'pro')
        self.assertEqual(self.b.post('/camera/auto-arm',json={'enabled':False},headers={'X-Set-ID':sid}).status_code,409)
        c.forms['right'].counter.reps=2;c.outputs['right']=c.forms['right'].base();c.aggregate()
        r=self.a.post('/camera/auto-arm',json={'enabled':False},headers={'X-Set-ID':sid});self.assertEqual(r.status_code,200,r.json);self.assertEqual(r.json['state']['difficulty'],'pro');self.assertNotEqual(r.json['state']['set_id'],sid)
        self.assertEqual(self.a.post('/camera/auto-arm',json={'enabled':True},headers={'X-Set-ID':sid}).status_code,409)
        self.assertEqual(self.a.get(f'/profiles/{self.pa}/rewards').json['wallet']['pro'],2)
        self.assertEqual(self.a.get('/leaderboard?exercise=curl&arm=auto').status_code,200)
    def test_bad_levels_and_unsupported_auto_have_no_side_effect(self):
        for value in ['bogus',None,1,{},[]]:self.assertEqual(self.start(difficulty=value).status_code,400)
        self.assertEqual(self.start(auto_arm='yes').status_code,400)
        self.assertEqual(self.a.post('/start',json=dict(profile_id=self.pa,exercise='goblet_squat',arm='right',auto_arm=True)).status_code,400)
    def test_character_account_persistence_private_dimensions_and_growth(self):
        url=f'/profiles/{self.pa}/character';initial=self.a.get(url).json;self.assertEqual(sum(initial['growth']['reps'].values()),0)
        payload=dict(appearance=dict(character.DEFAULT,gender='female',hair='ponytail',skin_color='#c0a0ff'),dimensions=dict(height_cm=180,weight_kg=75))
        r=self.a.post(url,json=payload);self.assertEqual(r.status_code,200,r.json)
        self.assertEqual(self.b.post(url,json=payload).status_code,404);self.assertEqual(self.b.get(url).status_code,404)
        self.store.save_set('left',self.pa,'curl','left',25,0,25,0,{})
        self.store.save_set('leg',self.pa,'goblet_squat','right',9000,0,0,9000,{})
        rewards.save_quality(self.store,'left',self.pa,'curl','left',25,0,0,accepted=25)
        rewards.save_quality(self.store,'leg',self.pa,'goblet_squat','right',9000,0,0,accepted=9000)
        d=character.overview(LeaderboardStore(self.store.path),self.pa,True);self.assertEqual(d['appearance'],payload['appearance']);self.assertEqual(d['dimensions'],payload['dimensions']);self.assertEqual(d['growth']['parts']['legs']['total_exp'],90000);self.assertGreater(d['growth']['levels']['legs'],0);self.assertLess(d['growth']['levels']['legs'],1);self.assertEqual(d['growth']['arm_reps'],dict(left=25,right=0));self.assertEqual(d['growth']['reps']['chest'],0)
        public=self.b.get(f'/social/characters/{self.pa}');self.assertEqual(public.status_code,200);self.assertNotIn('dimensions',public.json);self.assertEqual(public.json['visual'],d['visual']);self.assertEqual(public.json['appearance'],d['appearance'])
        self.assertEqual(self.a.post('/profiles',json={'name':'Second'}).status_code,400)
        # A pre-v30 profile remains available without permitting new duplicates.
        with self.store.connect() as db:
            other=db.execute("INSERT INTO profiles(name) VALUES('Second')").lastrowid
            db.execute('INSERT INTO profile_owners(profile_id,owner) SELECT ?,owner FROM profile_owners WHERE profile_id=?',(other,self.pa))
        self.assertEqual(self.a.get(f'/profiles/{other}/character').json['appearance'],payload['appearance'])
        self.assertEqual(self.a.get(f'/profiles/{self.pa}/overview').json['dimensions'],payload['dimensions'])
    def test_character_validation_does_not_overwrite(self):
        url=f'/profiles/{self.pa}/character';before=self.a.get(url).json['appearance']
        for a in [dict(character.DEFAULT,hair='evil'),dict(character.DEFAULT,hair_color='<script>'),dict(character.DEFAULT,gender=[]),dict(character.DEFAULT,unexpected=True)]:
            self.assertEqual(self.a.post(url,json=dict(appearance=a)).status_code,400)
            self.assertEqual(self.a.get(url).json['appearance'],before)
        self.assertEqual(self.a.post(url,json=dict(appearance=character.DEFAULT,dimensions=dict(height_cm=float('inf'),weight_kg=50))).status_code,400)
    def test_coins_cannot_be_injected_and_any_account_can_read(self):
        self.assertEqual(self.a.get(f'/profiles/{self.pa}/rewards').status_code,200)
        self.assertEqual(self.b.get(f'/profiles/{self.pa}/rewards').status_code,404)
        self.assertEqual(self.a.post(f'/profiles/{self.pa}/rewards',json=dict(action='award',coins=999,request_id=str(uuid.uuid4()))).status_code,400)
        for currency in [[],{},None,1,'universal']:
            self.assertEqual(self.a.post(f'/profiles/{self.pa}/rewards',json=dict(action='exchange',currency=currency,request_id=str(uuid.uuid4()))).status_code,400)
        self.assertEqual(sum(self.a.get(f'/profiles/{self.pa}/rewards').json['wallet'].values()),0)

if __name__=='__main__':unittest.main()
