"""Directional guard and armor lifecycle; older/tracking rooms keep their rules."""
import unittest
from unittest.mock import patch
import boxing,boxing_cage as cage,test_boxing as legacy
import test_boxing_cage as fixtures
class GuardMath(unittest.TestCase):
    def target(self,side='left',armor=10):return dict(hp=10,armor=armor,guard_side=side,guard_until=10.65,control_at=10)
    def test_matching_side_costs_nothing(self):
        for hand in ['left','right']:
            p=self.target(hand);e=cage.defend(p,hand,4,10.2);self.assertEqual((p['hp'],p['armor']),(10,10));self.assertEqual(e['guard_result'],'perfect');self.assertEqual(e['armor_damage'],0)
    def test_wrong_side_hits_hp_without_spending_armor(self):
        p=self.target('left');e=cage.defend(p,'right',4,10.2);self.assertEqual((p['hp'],p['armor']),(6,10));self.assertEqual(e['guard_result'],'wrong')
    def test_general_guard_damage_and_overflow(self):
        for armor,hp,left in [(10,10,6),(2,8,0),(0,6,0)]:
            p=self.target('both',armor);e=cage.defend(p,'right',4,10.2);self.assertEqual((p['hp'],p['armor']),(hp,left));self.assertEqual(e['armor_damage'],min(4,armor))
    def test_broken_correct_side_reduces_ten_percent(self):
        p=self.target('right',0);e=cage.defend(p,'right',4,10.2);self.assertEqual(p['hp'],6.4);self.assertEqual(e['damage'],3.6);self.assertEqual(e['guard_result'],'reduced')
        p=self.target('left',0);cage.defend(p,'left',1,10.2);self.assertEqual(p['hp'],9.1)
    def test_stale_guard_does_not_reduce_damage(self):
        p=self.target('left',0);cage.defend(p,'left',4,10.7);self.assertEqual(p['hp'],6)
    def test_regeneration_boundaries_cap_and_no_resurrection(self):
        p=dict(armor=7);q=dict(armor=0);m=dict(rules=6,control_mode='computer',status='active',round_start=10,players=[p,q])
        cage.regenerate(m,14.999);self.assertEqual(p['armor'],7)
        cage.regenerate(m,15);self.assertEqual(p['armor'],8)
        cage.regenerate(m,15);self.assertEqual(p['armor'],8)
        cage.regenerate(m,40);self.assertEqual((p['armor'],q['armor']),(10,0))
        p['armor']=3;m['status']='round_break';cage.regenerate(m,100);self.assertEqual(p['armor'],3)
    def test_tracking_and_existing_rules_unchanged(self):
        for mode,rules in [('tracking',6),('computer',5)]:
            p=dict(armor=7);m=dict(rules=rules,control_mode=mode,status='active',round_start=10,players=[p]);cage.regenerate(m,30);self.assertEqual(p['armor'],7);self.assertFalse(cage.directional_rules(m))
class GuardRoutes(unittest.TestCase):
    create=legacy.BoxingTests.create;act=legacy.BoxingTests.act;control=fixtures.CageRoutes.control;snapshot=fixtures.CageRoutes.snapshot;strike=fixtures.CageRoutes.strike;impact=fixtures.CageRoutes.impact
    def setUp(self):
        legacy.BoxingTests.setUp(self);rules=patch('boxing.MATCH_RULES',6);rules.start();self.addCleanup(rules.stop)
        self.create('computer');self.act(self.b,'accept');self.act(self.a,'ready');self.act(self.b,'ready');self.now+=5;self.seq={id(self.a):0,id(self.b):0}
    def test_actual_left_right_and_combined_guard(self):
        self.control(self.b,guard=True,guard_side='left');self.strike('left');m=self.impact();self.assertEqual(m['event']['guard_result'],'perfect');self.assertEqual(m['players'][1]['armor'],10)
        self.now+=.3;self.control(self.b,guard=True,guard_side='left');self.strike('right');m=self.impact();self.assertEqual(m['players'][1]['hp'],6)
        self.now+=.3;self.control(self.b,guard=True,guard_side='both');self.strike('right');m=self.impact();self.assertEqual(m['players'][1]['armor'],6);self.assertEqual(m['players'][1]['hp'],6)
    def test_invalid_guard_and_release(self):
        for side in ['bad',1,True,{},[]]:self.assertEqual(self.control(self.b,guard=True,guard_side=side).status_code,400)
        self.assertEqual(self.control(self.b,guard=False,guard_side='left').status_code,400)
        self.control(self.b,guard=True,guard_side='right');self.control(self.b,guard=False);self.strike('right');self.assertEqual(self.impact()['players'][1]['hp'],6)
    def test_regeneration_then_break_and_round_reset(self):
        for _ in range(3):
            self.control(self.b,guard=True,guard_side='both');self.strike('right');self.impact();self.now+=.3
        m=self.snapshot();self.assertEqual(m['players'][1]['armor'],0);self.assertEqual(m['players'][1]['hp'],8)
        for _ in range(6):self.now+=1;self.control(self.a);self.control(self.b)
        self.assertEqual(self.snapshot()['players'][1]['armor'],0)
        self.control(self.b,guard=True,guard_side='right');self.strike('right');self.assertEqual(self.impact()['players'][1]['hp'],4.4)
        for _ in range(2):self.now+=.5;self.control(self.b,guard=False);self.strike('right');self.impact()
        m=self.snapshot();self.assertEqual(m['status'],'round_break');self.now=m['next_round_at'];m=self.snapshot();self.assertEqual(m['players'][1]['armor'],10);self.assertEqual(m['players'][1]['hp'],10);self.assertIsNone(m['players'][1]['guard_side'])
