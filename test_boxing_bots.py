"""New rooms: matched bot stats, bounded learning, timed parries and physical hits."""
from copy import deepcopy
import math, unittest
from unittest.mock import patch
import boxing, boxing_bot, boxing_cage as cage
import test_boxing as legacy
import test_boxing_cage as fixtures

class BotPolicy(unittest.TestCase):
    def test_levels_and_power_are_identical_in_both_difficulties(self):
        p=dict(uid=4,profile_id=8,damage={'left':3,'right':7},kick_damage=5,hp=10,armor=10,
            model=dict(appearance={'build':.45},growth={'level':8},visual={'scale':1.2}))
        original=deepcopy(p)
        for difficulty in ['easy','hard']:
            b=boxing_bot.create(p,difficulty,100)
            for key in ['damage','kick_damage','armor']:self.assertEqual(p[key],b[key])
            for key in ['growth','visual']:self.assertEqual(p['model'][key],b['model'][key])
            self.assertEqual(b['hp'],20 if difficulty=='easy' else 50);self.assertEqual(b['max_hp'],b['hp'])
            self.assertNotEqual(b['model']['appearance'],p['model']['appearance'])
        self.assertEqual(p,original)
    def test_easy_round_one_does_not_read_habits_and_later_is_bounded(self):
        learned=dict(left=12,right=1,duck=9,samples=10)
        first=boxing_bot.policy('easy',1,learned);second=boxing_bot.policy('easy',2,learned);hard=boxing_bot.policy('hard',1,learned)
        self.assertIsNone(first['favorite']);self.assertEqual(second['favorite'],'left')
        self.assertGreater(second['defense'],first['defense']);self.assertLess(second['defense'],hard['defense'])
        self.assertGreater(second['aggression'],hard['aggression']);self.assertGreater(second['reaction'],hard['reaction'])
        self.assertLessEqual(boxing_bot.policy('easy',99,learned)['defense'],.42)

class BotRoutes(unittest.TestCase):
    def setUp(self):
        legacy.BoxingTests.setUp(self);p=patch('boxing.MATCH_RULES',7);p.start();self.addCleanup(p.stop)
    def create_bot(self,difficulty='easy',mode='computer'):
        r=self.a.post('/social/boxing/bot',json={'profile':1,'difficulty':difficulty,'control_mode':mode})
        self.assertEqual(r.status_code,200,r.json);self.mid=r.json['match']['id'];return r.json['match']
    def post(self,**data):return self.a.post('/social/boxing/'+self.mid,json=data)
    def test_private_validation_and_duplicate_room(self):
        for data in [{},dict(profile=1,difficulty='extreme',control_mode='computer'),dict(profile=True,difficulty='easy',control_mode='computer')]:self.assertEqual(self.a.post('/social/boxing/bot',json=data).status_code,400)
        m=self.create_bot();self.assertEqual(m['players'][0]['damage'],m['players'][1]['damage'])
        self.assertEqual(self.b.get('/social/boxing/'+self.mid).status_code,404)
        self.assertEqual(self.a.post('/social/boxing/bot',json={'profile':1,'difficulty':'hard','control_mode':'computer'}).status_code,409)
        self.assertEqual(len(self.a.get('/social/boxing').json['matches']),1)
    def test_server_bot_fights_and_does_not_disconnect(self):
        self.create_bot();m=self.post(action='ready').json['match'];self.now=m['start']
        for i in range(60):
            self.now+=.15;m=self.post(action='heartbeat').json['match']
        self.assertIn(m['status'],['active','round_break']);self.assertTrue(any(e['attacker']==-1 for e in m['events']))
        self.assertLess(m['players'][0]['hp'],10);self.assertEqual(m['players'][1]['hp'],20)
        self.assertGreater(m['players'][1]['last_punch'],0)
        self.assertNotIn('winner',m)
    def test_bot_still_obeys_human_input_mode_and_disconnect(self):
        self.create_bot(mode='tracking');m=self.post(action='ready').json['match'];self.now=m['start']
        r=self.post(action='control',seq=1,input_source='keyboard',internal_bot=True,dash=True,strafe=1)
        self.assertEqual(r.status_code,400)
        self.now+=21;m=self.post(action='heartbeat').json['match'];self.assertEqual(m['result'],'disconnect')
        self.assertNotIn('belt_awarded',m)
    def test_round_learning_reset_and_best_of_three(self):
        m=self.create_bot();boxing.action(m,self.uid,{'action':'ready'},self.now);self.now=m['start'];boxing.advance(m,self.now)
        m['brain']['observed']=dict(left=10,right=1,duck=8,samples=10)
        boxing.knockout(m,m['players'][0],self.now+2);boxing.advance(m,self.now+12)
        self.assertEqual(m['round'],2);self.assertEqual(m['brain']['plan']['favorite'],'left')
        self.assertEqual([p['hp'] for p in m['players']],[10,20]);self.assertEqual(m['players'][0]['wins'],1)
        m['players'][0]['seen']=self.now+13;boxing.knockout(m,m['players'][0],self.now+13);boxing.advance(m,self.now+23)
        self.assertEqual(m['status'],'finished');self.assertEqual(m['winner'],self.uid)
    def test_hard_reads_visible_guard_and_duck_without_bonus_damage(self):
        m=self.create_bot('hard');boxing.action(m,self.uid,{'action':'ready'},self.now);self.now=m['start'];boxing.advance(m,self.now)
        human=m['players'][0];human.update(guard_until=self.now+3,guard_side='left',crouch=.8,control_at=self.now+.1)
        boxing.advance(m,self.now+.11)
        m['brain']['next_attack']=0;calls=[]
        boxing_bot.tick(m,self.now+.3,lambda *args,**kw:calls.append(args[2]))
        self.assertEqual(calls[-1]['action'],'right');self.assertEqual(calls[-1]['punch_type'],'uppercut')
        self.assertEqual(m['players'][1]['damage'],human['damage'])
    def test_delayed_decisions_and_no_catchup_attack_burst(self):
        m=self.create_bot('hard');boxing.action(m,self.uid,{'action':'ready'},self.now);self.now=m['start'];boxing.advance(m,self.now)
        bot=m['players'][1];self.assertEqual(bot['last_punch'],0)
        m['players'][0].update(last_punch=self.now+.01,last_hand='left',punch_type='hook')
        boxing.advance(m,self.now+.1);self.assertEqual(m['brain']['observed'],{})
        boxing.advance(m,self.now+.3);self.assertEqual(m['brain']['observed']['left'],1)
        boxing.advance(m,self.now+.5);self.assertEqual(m['brain']['observed']['left'],1)
        boxing.advance(m,self.now+10);self.assertLessEqual(len(m['pending_strikes']),1)

class ParryRoutes(unittest.TestCase):
    create=legacy.BoxingTests.create;act=legacy.BoxingTests.act;control=fixtures.CageRoutes.control;snapshot=fixtures.CageRoutes.snapshot;strike=fixtures.CageRoutes.strike;impact=fixtures.CageRoutes.impact
    def setUp(self):
        legacy.BoxingTests.setUp(self);p=patch('boxing.MATCH_RULES',7);p.start();self.addCleanup(p.stop)
        self.create('computer');self.act(self.b,'accept');self.act(self.a,'ready');self.act(self.b,'ready');self.now+=5;self.seq={id(self.a):0,id(self.b):0}
    def parry(self,hand='left',side=-1,kind='straight'):
        self.strike(hand,kind);self.now+=.08;self.control(self.b,dash=True,strafe=side);self.now+=.12;return self.snapshot()
    def test_opposite_dash_parries_and_grants_single_immediate_counter(self):
        # A prior strike still recovering does not prevent the earned counter.
        self.control(self.b,'left',strike_id='prior');self.now+=.01
        m=self.parry();self.assertEqual(m['event']['result'],'parry');self.assertEqual(m['players'][1]['hp'],10)
        m=self.control(self.b,'right',strike_id='counter').json['match'];queued=m['pending_strikes'][-1]
        self.assertTrue(queued['counter']);self.assertAlmostEqual(queued['time']-self.now,.1)
        count=len(m['pending_strikes']);m=self.control(self.b,'left',strike_id='spam').json['match'];self.assertEqual(len(m['pending_strikes']),count)
        self.assertEqual(m['players'][1]['counter_until'],0)
    def test_right_punch_requires_left_dash(self):self.assertEqual(self.parry('right',1)['event']['result'],'parry')
    def test_wrong_side_only_dodges_and_no_counter(self):
        m=self.parry(side=1);self.assertEqual(m['event']['result'],'dodge');self.assertFalse(m['players'][1].get('counter_until',0))
    def test_uppercut_cannot_be_parried(self):self.assertEqual(self.parry(kind='uppercut')['event']['result'],'hit')
    def test_kick_cannot_be_parried(self):
        self.parry(kind='kick');self.now+=.1;self.assertNotEqual(self.snapshot()['event']['result'],'parry')
    def test_expired_window_cannot_override_cooldown(self):
        m=self.parry();self.now=m['players'][1]['counter_until']+.01
        self.control(self.b,'left',strike_id='normal');m=self.control(self.b,'right',strike_id='too-fast').json['match']
        own=[s for s in m['pending_strikes'] if s['attacker']==self.other];self.assertEqual(len(own),1);self.assertFalse(own[0]['counter'])
    def test_hits_push_but_blocks_do_not(self):
        self.strike();m=self.impact();self.assertGreater(m['players'][1]['x'],.7);self.assertAlmostEqual(m['event']['knockback']['x'],.14)
        self.now+=.3;self.control(self.b,guard=True,guard_side='left');self.strike();m=self.impact();self.assertEqual(m['event']['result'],'block');self.assertNotIn('knockback',m['event'])
    def test_forged_counter_is_ignored(self):
        self.strike();m=self.control(self.a,'right',strike_id='fake',counter_until=self.now+10,counter=True).json['match'];self.assertEqual(len(m['pending_strikes']),1)
    def test_early_dash_and_far_away_dash_do_not_parry(self):
        self.control(self.b,dash=True,strafe=-1);self.now+=.5;self.strike();self.assertNotEqual(self.impact()['event']['result'],'parry')
    def test_wall_clamps_knockback(self):
        m=self.snapshot();m['players'][0].update(x=3.6,z=0);m['players'][1].update(x=4.95,z=0)
        cage.queue(m,*m['players'],'right','uppercut',self.now,'wall');cage.resolve(m,self.now+.2,boxing.knockout)
        self.assertLessEqual(m['players'][1]['x'],5);self.assertLessEqual(m['event']['knockback']['x'],.051)
