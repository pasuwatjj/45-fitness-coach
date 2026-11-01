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
        rules=patch('boxing.MATCH_RULES',5);rules.start();self.addCleanup(rules.stop)
        self.start();self.seq={id(self.a):0,id(self.b):0}
    def control(self,client,action='control',**kw):
        self.seq[id(client)]+=1
        return self.act(client,action,self.seq[id(client)],**kw)
    def snapshot(self):return self.act(self.a,'heartbeat').json['match']
    def strike(self,hand='left',kind='straight'):
        return self.control(self.a,hand,punch_type=kind,strike_id='strike:'+str(self.seq[id(self.a)]+1))
    def impact(self):self.now+=.2;return self.snapshot()
    def test_room_control_mode_is_required_and_shared(self):
        for mode in [None,'bot','mixed',[],True]:
            r=self.a.post('/social/boxing/invite',json={'friend':self.other,'profile':1,'control_mode':mode})
            self.assertEqual(r.status_code,400)
        self.act(self.a,'leave');self.now+=6;m=self.create('computer');self.assertEqual(m['control_mode'],'computer')
        self.assertEqual(self.act(self.b,'accept',control_mode='tracking').status_code,400)
        self.assertEqual(self.act(self.b,'accept').json['match']['control_mode'],'computer')
        self.assertEqual(self.act(self.b,'ready',control_mode='tracking').status_code,400)
        self.assertEqual(self.act(self.b,'ready',control_mode='computer').status_code,200)
        self.assertEqual(self.b.get('/social/boxing/'+self.mid).json['match']['control_mode'],'computer')

    def test_keyboard_motion_and_leg_strike(self):
        self.act(self.a,'leave');self.now+=6;self.create('computer');self.act(self.b,'accept');self.act(self.a,'ready');self.act(self.b,'ready');self.now+=5
        self.assertEqual(self.act(self.a,'control',1,strafe=1).status_code,200)
        self.now+=.2;m=self.act(self.a,'heartbeat').json['match'];self.assertLess(m['players'][0]['z'],-.1)
        self.assertEqual(self.act(self.a,'control',2,strafe=True).status_code,400)
        self.act(self.a,'control',2,strafe=0);self.now+=.2
        self.assertEqual(self.act(self.a,'left',3,punch_type='kick',strike_id='kick-one').status_code,200)
        self.now+=.3;m=self.act(self.a,'heartbeat').json['match'];self.assertEqual(m['event']['punch_type'],'kick');self.assertEqual(m['event']['damage'],1);self.assertEqual(m['players'][1]['hp'],9)
        self.now+=.5;self.act(self.a,'left',4,punch_type='kick',strike_id='kick-one');self.now+=.4
        self.assertEqual(self.act(self.a,'heartbeat').json['match']['players'][1]['hp'],9)

    def test_simultaneous_dash_cannot_cross_opponent_or_cage(self):
        ps=[dict(x=x,z=0,control_at=10,move=1,side=0,side_since=None,dash_at=10,dash_until=10.18,dash_move=1,dash_side=0) for x in [-.41,.41]]
        m=dict(players=ps,motion_at=10,start=10);cage.motion(m,10.18)
        self.assertLess(ps[0]['x'],ps[1]['x']);self.assertAlmostEqual(ps[1]['x']-ps[0]['x'],.8)
        p=dict(x=4.9,z=0,control_at=10,move=-1,side=0,side_since=None,dash_at=10,dash_until=10.18,dash_move=-1,dash_side=0)
        cage.motion(dict(players=[p],motion_at=10,start=10),10.18);self.assertLessEqual(p['x'],5.0)

    def test_dash_timing_cooldown_and_mode_validation(self):
        self.assertEqual(self.act(self.a,'control',1,move=1,dash=True).status_code,400)
        self.act(self.a,'leave');self.now+=6;self.create('computer');self.act(self.b,'accept');self.act(self.a,'ready');self.act(self.b,'ready');self.now+=5
        before=self.snapshot()['players'][0]['x']
        self.act(self.a,'control',1,move=-1,dash=True);self.now+=.18;m=self.snapshot();p=m['players'][0]
        self.assertAlmostEqual(before-p['x'],cage.SPEED*.18*2.6,places=5);started=p['last_dash']
        self.act(self.a,'control',2,move=-1,dash=True);self.assertEqual(self.snapshot()['players'][0]['last_dash'],started)
        self.assertEqual(self.act(self.a,'control',3,dash='yes').status_code,400)
        self.act(self.a,'control',3,move=0);self.now+=.5;stopped=self.snapshot()['players'][0]['x'];self.now+=.2;self.assertEqual(self.snapshot()['players'][0]['x'],stopped)
        self.act(self.a,'control',4,strafe=1,dash=True);self.assertGreater(self.snapshot()['players'][0]['last_dash'],started)

    def test_tracking_room_rejects_keyboard_kicks(self):
        r=self.act(self.a,'left',1,punch_type='kick',strike_id='not-tracked');self.assertEqual(r.status_code,400)

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
    def test_gentle_evasion_without_moving_and_stale_reset(self):
        for posture in [{'slip':-.40},{'bend':.28},{'bend':-.16},{'crouch':.55}]:
            self.now+=1
            before=self.snapshot()['players'][1]
            self.control(self.b,**posture);self.strike();m=self.impact()
            self.assertEqual(m['event']['result'],'dodge')
            self.assertEqual((m['players'][1]['x'],m['players'][1]['z']),(before['x'],before['z']))
            self.now+=.8;self.strike();self.assertEqual(self.impact()['event']['result'],'hit')
    def test_strike_identity_is_exactly_once_and_payload_validated(self):
        self.control(self.a,'left',strike_id='same');m=self.impact();self.assertEqual(len(m['events']),1)
        self.now+=1;self.control(self.a,'left',strike_id='same');m=self.impact();self.assertEqual(len(m['events']),1);self.assertEqual(m['players'][1]['hp'],8)
        for kwargs in [{'slip':float('nan')},{'bend':2},{'slip':True},{'bend':'1'}]:self.assertEqual(self.control(self.a,**kwargs).status_code,400)
        for token in [None,{},'','a'*101]:self.assertEqual(self.control(self.a,'right',strike_id=token).status_code,400)
    def test_server_two_second_hold_continuous_reversal_release_and_stale_stop(self):
        start=self.snapshot()['players'][0]
        for i in range(20):self.control(self.a,slip=.8);self.now+=.1
        p=self.snapshot()['players'][0];self.assertAlmostEqual(p['z'],start['z'],places=5)
        for i in range(6):self.control(self.a,slip=.8);self.now+=.1
        p=self.snapshot()['players'][0];self.assertLess(p['z'],-.4);z=p['z']
        self.control(self.a,slip=-.8);self.now+=.3;self.assertGreater(self.snapshot()['players'][0]['z'],z+.1);z=self.snapshot()['players'][0]['z']
        self.control(self.a,slip=0);self.now+=.3;self.assertAlmostEqual(self.snapshot()['players'][0]['z'],z)
        self.control(self.a,move=-1);self.now+=1;p=self.snapshot()['players'][0];self.now+=2;q=self.snapshot()['players'][0];self.assertEqual((p['x'],p['z']),(q['x'],q['z']));self.assertEqual(q['armor'],10)
    def test_continuous_axis_switch_and_neutral_rearm(self):
        self.control(self.a,move=1);self.now+=.12
        self.control(self.a,slip=.8);self.now+=.2
        p=self.snapshot()['players'][0];self.assertTrue(p['travel_ready']);self.assertLess(p['z'],-.1)
        self.control(self.a);self.now+=.12;self.control(self.a,slip=-.8);self.now+=.2
        q=self.snapshot()['players'][0];self.assertTrue(q['travel_ready']);self.assertGreater(q['z'],p['z'])
        self.control(self.a);self.now+=.3;stopped=self.snapshot()['players'][0]['z'];self.control(self.a,slip=.8);self.now+=.2
        q=self.snapshot()['players'][0];self.assertFalse(q['travel_ready']);self.assertAlmostEqual(q['z'],stopped)
    def test_early_reversal_restarts_the_hold(self):
        for _ in range(15):self.control(self.a,slip=.8);self.now+=.1
        before=self.snapshot()['players'][0]['z']
        for _ in range(15):self.control(self.a,slip=-.8);self.now+=.1
        self.assertAlmostEqual(self.snapshot()['players'][0]['z'],before)
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
    def test_two_rounds_knockdown_recovery_single_belt_and_cancelled_strikes(self):
        for round_no in [1,2]:
            for i in range(3):
                self.strike('right');m=self.impact();self.now+=.3
            self.assertEqual(m['players'][0]['wins'],round_no);self.assertEqual(m['pending_strikes'],[])
            if round_no==1:
                self.assertEqual(m['status'],'round_break');down=m['knockdown'];self.assertEqual(down['uid'],self.other);self.assertEqual(down['recover_at'],down['at']+10)
                self.assertFalse(m.get('belt_awarded'));self.assertEqual(self.a.get('/social/boxing/belts/'+str(self.pa)).json['belts'],0)
                self.assertEqual(self.control(self.b,'left',strike_id='while-down').status_code,400)
                self.now=m['next_round_at']-.01;self.assertEqual(self.snapshot()['status'],'round_break')
                self.now=m['next_round_at'];m=self.snapshot();self.assertEqual([p['hp'] for p in m['players']],[10,10]);self.assertNotIn('knockdown',m);self.act(self.b,'heartbeat')
        self.assertEqual(m['status'],'round_break');self.assertFalse(m.get('belt_awarded'))
        self.now=m['next_round_at']-.01;self.assertEqual(self.snapshot()['status'],'round_break')
        self.now=m['next_round_at'];m=self.snapshot()
        self.assertEqual(m['winner'],self.uid);self.assertTrue(m['belt_awarded']);self.assertIsNone(m['knockdown']['recover_at'])
        for i in range(3):self.snapshot()
        self.assertEqual(self.a.get('/social/boxing/trophies/'+str(self.pa)).json['trophies'],1)
        self.assertEqual(self.a.get('/social/boxing/belts/'+str(self.pa)).json['belts'],1)
        self.assertEqual(self.b.get('/social/boxing/belts/'+str(self.pa)).status_code,404)
        self.assertEqual(self.b.get('/social/boxing/belts/'+str(self.pb)).json['belts'],0)
    def test_upper_body_posture_sync_and_clear(self):
        posture=dict(turn=.8,hipTurn=.25,tilt=-.3,headPitch=-.7,headYaw=.4,headRoll=.2)
        r=self.control(self.a,posture=posture,bend=-.7);self.assertEqual(r.status_code,200)
        self.assertEqual(self.b.get('/social/boxing/'+self.mid).json['match']['players'][0]['posture'],posture)
        self.assertIsNone(self.control(self.a,'idle').json['match']['players'][0]['posture'])
    def test_lower_body_sync_and_validation(self):
        body=dict(confidence=1,shiftX=.6,shiftZ=-.4,drop=.3,hipRoll=.2,leftKnee=.6,rightKnee=.3,stance=.2,stagger=-.2)
        r=self.control(self.a,lowerBody=body);self.assertEqual(r.status_code,200)
        self.assertEqual(self.b.get('/social/boxing/'+self.mid).json['match']['players'][0]['lowerBody'],body)
        for bad in [{},[],dict(body,shiftX=2),dict(body,confidence=-1),dict(body,drop=True),dict(body,leftKnee=float('nan'))]:self.assertEqual(self.control(self.a,lowerBody=bad).status_code,400)
        self.assertIsNone(self.control(self.a,'idle').json['match']['players'][0]['lowerBody'])
    def test_invalid_upper_body_posture_rejected(self):
        good=dict(turn=0,hipTurn=0,tilt=0,headPitch=0,headYaw=0,headRoll=0)
        for value in [[],{},dict(good,extra=0),dict(good,turn=1.1),dict(good,headPitch=True),dict(good,headRoll=float('nan'))]:
            self.assertEqual(self.control(self.a,posture=value).status_code,400)
    def test_historical_victories_are_preserved_as_belts(self):
        self.snapshot()
        with self.store.connect() as db:
            db.execute('INSERT INTO boxing_trophies VALUES(?,?,?,?)',('historical-victory',self.uid,self.pa,self.now-100))
        self.assertEqual(self.a.get('/social/boxing/belts/'+str(self.pa)).json['belts'],1)
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
