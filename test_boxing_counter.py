"""Matching punches cancel together; different, late and distant strikes do not."""
import json,unittest
from unittest.mock import patch
import boxing
import test_boxing as legacy

class CounterTests(unittest.TestCase):
    create=legacy.BoxingTests.create
    act=legacy.BoxingTests.act
    def setUp(self):
        legacy.BoxingTests.setUp(self)
        rules=patch.object(boxing,'MATCH_RULES',9);rules.start();self.addCleanup(rules.stop)
        self.create('computer');self.act(self.b,'accept');self.act(self.a,'ready');self.act(self.b,'ready');self.now+=5
        self.act(self.a,'heartbeat')
    def pair(self,hand='left',kind='straight',delay=.05,other_hand=None,other_kind=None):
        self.act(self.a,hand,1,strike_id='a',punch_type=kind)
        self.now+=delay
        self.act(self.b,other_hand or hand,1,strike_id='b',punch_type=other_kind or kind)
        self.now+=.4
        return self.act(self.a,'heartbeat').json['match']
    def test_matching_punches_zero_hp_and_armor_once(self):
        m=self.pair();self.assertEqual(m['event']['result'],'counter')
        self.assertEqual([(p['hp'],p['armor']) for p in m['players']],[(10,10),(10,10)])
        self.assertEqual(m['event']['damage'],0);self.assertEqual(m['event']['hp_damage'],0);self.assertEqual(m['event']['armor_damage'],0)
        self.assertEqual(m['pending_strikes'],[]);self.assertEqual(len(m['events']),1)
        self.assertTrue(all(p['clash_hand']=='left' and p['clash_at'] for p in m['players']))
        self.now+=1;again=self.act(self.b,'heartbeat').json['match'];self.assertEqual(again['events'],m['events'])
        self.act(self.a,'left',2,strike_id='a');self.assertEqual(self.act(self.b,'heartbeat').json['match']['pending_strikes'],[])
    def test_right_uppercuts_also_rebound(self):
        m=self.pair('right','uppercut');self.assertEqual(m['event']['result'],'counter');self.assertTrue(all(p['hp']==10 for p in m['players']))
    def test_different_hands_still_land(self):
        m=self.pair(other_hand='right');self.assertEqual([p['hp'] for p in m['players']],[6,8]);self.assertNotIn('counter',[e['result'] for e in m['events']])
    def test_different_types_still_land(self):
        m=self.pair(other_kind='uppercut');self.assertEqual([p['hp'] for p in m['players']],[8,8])
    def test_outside_contact_window_does_not_cancel(self):
        m=self.pair(delay=.15);self.assertNotIn('counter',[e['result'] for e in m['events']]);self.assertEqual([p['hp'] for p in m['players']],[8,8])
    def test_late_input_never_refunds_landed_damage(self):
        m=self.pair(delay=.3);self.assertNotIn('counter',[e['result'] for e in m['events']]);self.assertEqual([p['hp'] for p in m['players']],[8,8])
    def test_kicks_are_not_fist_counters(self):
        m=self.pair(kind='kick');self.assertEqual([p['hp'] for p in m['players']],[9,9])
    def test_out_of_range_does_not_show_counter(self):
        m=self.act(self.a,'heartbeat').json['match'];m['players'][1]['x']=4
        with self.store.connect() as db:db.execute('UPDATE boxing_matches SET state=? WHERE id=?',(json.dumps(m),self.mid))
        m=self.pair();self.assertTrue(all(e['result']=='miss' for e in m['events']))
    def test_tracking_hooks_use_same_rule(self):
        self.act(self.a,'leave');self.create('tracking');self.act(self.b,'accept');self.act(self.a,'ready');self.act(self.b,'ready');self.now+=5
        m=self.pair(kind='hook');self.assertEqual(m['event']['result'],'counter')
    def test_slow_clock_keeps_matching_window(self):
        self.act(self.a,'skill');m=self.pair(delay=.2)
        self.assertEqual(m['event']['result'],'counter');self.assertTrue(all(p['hp']==10 for p in m['players']))

if __name__=='__main__':unittest.main()
