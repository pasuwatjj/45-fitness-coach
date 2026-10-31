"""Cage rules: authoritative movement, timed impacts and upper-body evasion."""
import math,unittest
from unittest.mock import patch
import boxing,boxing_cage as cage
import test_boxing as legacy
class CageRoutes(unittest.TestCase):
    create=legacy.BoxingTests.create
    act=legacy.BoxingTests.act
    start=legacy.BoxingTests.start
    def setUp(self):
        legacy.BoxingTests.setUp(self)
        rules=patch('boxing.MATCH_RULES',4);rules.start();self.addCleanup(rules.stop)
        self.start();self.seq={id(self.a):0,id(self.b):0}
    def control(self,client,action='control',**kw):
        self.seq[id(client)]+=1
        return self.act(client,action,self.seq[id(client)],**kw)
    def snapshot(self):return self.act(self.a,'heartbeat').json['match']
    def strike(self,hand='left',kind='straight'):
        return self.control(self.a,hand,punch_type=kind,strike_id='strike:'+str(self.seq[id(self.a)]+1))
    def impact(self):self.now+=.2;return self.snapshot()
    def test_windup_allows_directional_reaction_and_no_armor_cost(self):
        self.assertEqual(self.strike().json['match']['players'][1]['hp'],10)
        self.now+=.10;self.control(self.b,slip=-.8)
        m=self.impact();self.assertEqual(m['event']['result'],'dodge');self.assertEqual(m['players'][1]['hp'],10);self.assertEqual(m['players'][1]['armor'],10)
        self.now+=.5;self.control(self.b,slip=.8);self.strike();m=self.impact();self.assertEqual(m['event']['result'],'hit');self.assertEqual(m['players'][1]['hp'],8)
    def test_right_punch_slip_left_and_stale_tracking(self):
        self.control(self.b,slip=.8);self.strike('right');self.assertEqual(self.impact()['event']['result'],'dodge')
        self.now+=.8;self.strike('right');self.assertEqual(self.impact()['event']['result'],'hit')
    def test_bow_and_crouch_evade_straight_hook_not_uppercut(self):
        for posture in [{'bend':.9},{'crouch':.9}]:
            for kind in ['straight','hook','uppercut']:
                self.now+=.5;self.control(self.b,**posture);self.strike(kind=kind)
                self.assertEqual(self.impact()['event']['result'],'hit' if kind=='uppercut' else 'dodge')
    def test_strike_identity_is_exactly_once_and_payload_validated(self):
        self.control(self.a,'left',strike_id='same');m=self.impact();self.assertEqual(len(m['events']),1)
        self.now+=1;self.control(self.a,'left',strike_id='same');m=self.impact();self.assertEqual(len(m['events']),1);self.assertEqual(m['players'][1]['hp'],8)
        for kwargs in [{'slip':float('nan')},{'bend':2},{'slip':True},{'bend':'1'}]:self.assertEqual(self.control(self.a,**kwargs).status_code,400)
        for token in [None,{},'','a'*101]:self.assertEqual(self.control(self.a,'right',strike_id=token).status_code,400)
    def test_server_five_second_hold_reversal_release_and_stale_stop(self):
        start=self.snapshot()['players'][0]
        for i in range(50):self.control(self.a,slip=.8);self.now+=.1
        p=self.snapshot()['players'][0];self.assertAlmostEqual(p['z'],start['z'],places=5)
        for i in range(6):self.control(self.a,slip=.8);self.now+=.1
        p=self.snapshot()['players'][0];self.assertLess(p['z'],-.4);z=p['z']
        self.control(self.a,slip=-.8);self.now+=.3;self.assertAlmostEqual(self.snapshot()['players'][0]['z'],z)
        self.control(self.a,slip=0);self.now+=.3;self.assertAlmostEqual(self.snapshot()['players'][0]['z'],z)
        self.control(self.a,move=-1);self.now+=1;p=self.snapshot()['players'][0];self.now+=2;q=self.snapshot()['players'][0];self.assertEqual((p['x'],p['z']),(q['x'],q['z']));self.assertEqual(q['armor'],10)
    def test_hold_cannot_be_spoofed_by_strafe_or_missing_frames(self):
        self.control(self.a,strafe=1);self.now+=.5;self.assertEqual(self.snapshot()['players'][0]['z'],0)
        self.control(self.a,slip=.8);self.now+=5;self.control(self.a,slip=.8);self.assertEqual(self.snapshot()['players'][0]['side_since'],self.now);self.assertEqual(self.snapshot()['players'][0]['z'],0)
    def test_range_and_movement_no_armor_cost(self):
        for i in range(8):self.control(self.b,move=-1);self.now+=.2
        self.strike();m=self.impact();self.assertEqual(m['event']['result'],'miss');self.assertEqual([p['armor'] for p in m['players']],[10,10])
    def test_guard_only_loses_armor_on_block(self):
        for i in range(8):self.control(self.b,guard=True);self.now+=.4
        self.control(self.b,guard=True);self.strike();m=self.impact();self.assertEqual(m['event']['result'],'block');self.assertEqual(m['players'][1]['armor'],9);self.assertEqual(m['players'][1]['hp'],10)
        self.now+=.5;self.control(self.b,guard=True,slip=-1);self.strike();m=self.impact();self.assertEqual(m['event']['result'],'dodge');self.assertEqual(m['players'][1]['armor'],9)
    def test_two_rounds_single_trophy_and_queued_strikes_cancelled(self):
        for round_no in [1,2]:
            for i in range(3):
                self.strike('right');m=self.impact();self.now+=.3
            self.assertEqual(m['players'][0]['wins'],round_no);self.assertEqual(m['pending_strikes'],[])
            if round_no==1:
                self.assertEqual(m['status'],'round_break');self.now=m['next_round_at'];m=self.snapshot();self.assertEqual([p['hp'] for p in m['players']],[10,10])
        self.assertEqual(m['winner'],self.uid)
        for i in range(3):self.snapshot()
        self.assertEqual(self.a.get('/social/boxing/trophies/'+str(self.pa)).json['trophies'],1)
    def test_leave_cancels_windup(self):
        self.strike();m=self.act(self.b,'leave').json['match'];self.assertEqual(m['pending_strikes'],[]);self.assertEqual(m['players'][1]['hp'],10)
class CageGeometry(unittest.TestCase):
    def test_boundaries(self):
        for x in range(-20,21,2):
            for z in range(-20,21,2):
                a,b=cage.clamp(x,z)
                self.assertTrue(all(a*math.cos(i*math.pi/4)+b*math.sin(i*math.pi/4)<=cage.APOTHEM+1e-8 for i in range(8)))
    def test_collision_and_diagonal_speed(self):
        ps=[dict(x=-1,z=0,move=1,side=1,side_since=0,control_at=10),dict(x=1,z=0,move=0,control_at=10)]
        m=dict(players=ps,motion_at=10,start=5);cage.motion(m,10.2);self.assertAlmostEqual(math.hypot(ps[0]['x']+1,ps[0]['z']),cage.SPEED*.2)
        ps[0].update(x=0,z=0);ps[1].update(x=0,z=0);cage.motion(m,10.2);self.assertAlmostEqual(math.hypot(ps[1]['x']-ps[0]['x'],ps[1]['z']-ps[0]['z']),.8)
if __name__=='__main__':unittest.main()
