"""Cinematic X is one right-arm hit, with 180 real seconds between activations."""
import json,unittest
from unittest.mock import patch
import boxing,boxing_special
import test_boxing as legacy

class SpecialTests(unittest.TestCase):
    create=legacy.BoxingTests.create
    act=legacy.BoxingTests.act
    def setUp(self):
        legacy.BoxingTests.setUp(self)
        rules=patch.object(boxing,'MATCH_RULES',9);rules.start();self.addCleanup(rules.stop)
        self.create('computer');self.act(self.b,'accept');self.act(self.a,'ready');self.act(self.b,'ready');self.now+=5;self.act(self.a,'heartbeat')
    def test_exact_one_arm_damage_at_impact_then_resume(self):
        started=self.now;m=self.act(self.a,'special').json['match'];game=m['combat_now']
        self.assertEqual(m['players'][0]['special_ready_at'],started+180);self.assertEqual(m['special']['damage'],4)
        self.now+=4.09;m=self.act(self.b,'heartbeat').json['match'];self.assertEqual(m['players'][1]['hp'],10);self.assertAlmostEqual(m['combat_now'],game)
        self.now+=.02;m=self.act(self.b,'heartbeat').json['match'];self.assertEqual(m['players'][1]['hp'],6);self.assertEqual(m['players'][1]['armor'],10)
        for _ in range(3):self.assertEqual(self.act(self.a,'heartbeat').json['match']['players'][1]['hp'],6)
        self.now=started+6.3;m=self.act(self.b,'heartbeat').json['match'];self.assertTrue(m['special']['complete']);self.assertAlmostEqual(m['combat_now']-game,.1)
    def test_no_inputs_or_stacking_and_180_second_cooldown(self):
        start=self.now;self.act(self.a,'special')
        self.assertEqual(self.act(self.a,'special').status_code,400);self.assertEqual(self.act(self.b,'special').status_code,400);self.assertEqual(self.act(self.b,'skill').status_code,400)
        self.now+=1;m=self.act(self.b,'right',2,strike_id='locked',move=1).json['match'];self.assertEqual(m['pending_strikes'],[]);self.assertTrue(all(p['move']==0 for p in m['players']))
        while self.now<start+179.9:
            self.now=min(start+179.9,self.now+10);self.act(self.a,'heartbeat');self.act(self.b,'heartbeat')
        self.assertEqual(self.act(self.a,'special').status_code,400)
        self.now=start+180;self.assertEqual(self.act(self.a,'special').status_code,200)
    def test_shared_slow_and_cinematic_pause_do_not_double_count(self):
        start=self.now;self.act(self.a,'skill');m=self.act(self.b,'special').json['match'];game=m['combat_now']
        self.now+=6.2;m=self.act(self.a,'heartbeat').json['match'];self.assertAlmostEqual(m['combat_now'],game)
        self.now+=1;m=self.act(self.b,'heartbeat').json['match'];self.assertAlmostEqual(m['combat_now']-game,.4)
        self.assertEqual(m['players'][1]['special_ready_at'],start+180);self.assertEqual(m['slow_until'],start+60)
    def test_out_of_range_does_not_spend_cooldown(self):
        m=self.act(self.a,'heartbeat').json['match'];m['players'][1]['x']=4.5
        with self.store.connect() as db:db.execute('UPDATE boxing_matches SET state=? WHERE id=?',(json.dumps(m),self.mid))
        self.assertEqual(self.act(self.a,'special').status_code,400);self.assertNotIn('special_ready_at',self.act(self.a,'heartbeat').json['match']['players'][0])
    def test_knockout_after_cinematic_and_no_duplicate_finisher(self):
        m=self.act(self.a,'heartbeat').json['match'];m['players'][1]['hp']=4;m['players'][0]['wins']=1
        with self.store.connect() as db:db.execute('UPDATE boxing_matches SET state=? WHERE id=?',(json.dumps(m),self.mid))
        self.act(self.a,'special');self.now+=4.2;m=self.act(self.b,'heartbeat').json['match'];self.assertEqual(m['players'][1]['hp'],0);self.assertEqual(m['status'],'active')
        self.now+=2.1;m=self.act(self.b,'heartbeat').json['match'];self.assertEqual(m['status'],'round_break');self.assertEqual(m['players'][0]['wins'],2);self.assertNotIn('finale',m)
        self.now+=10;m=self.act(self.a,'heartbeat').json['match'];self.assertEqual(m['status'],'finished');self.assertEqual(m['winner'],self.uid)
    def test_leave_cancels_cinematic_without_later_hit(self):
        self.act(self.a,'special');self.now+=1;self.act(self.a,'leave');self.now+=7;m=self.act(self.b,'heartbeat').json['match'];self.assertEqual(m['status'],'finished');self.assertEqual(m['players'][1]['hp'],10)

if __name__=='__main__':unittest.main()
