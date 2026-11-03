"""Two-account authoritative X evasion, pause, impact and cooldown regressions."""
import json
from unittest.mock import patch
import unittest
import boxing
import test_boxing as legacy

class AimTests(unittest.TestCase):
    create=legacy.BoxingTests.create
    act=legacy.BoxingTests.act
    def setUp(self):
        legacy.BoxingTests.setUp(self)
        rules=patch.object(boxing,'MATCH_RULES',11);rules.start();self.addCleanup(rules.stop)
        self.create('computer');self.act(self.b,'accept');self.act(self.a,'ready');self.act(self.b,'ready')
        self.now+=5;self.act(self.a,'heartbeat')
        self.mutate(lambda m:[p.update(max_hp=10) for p in m['players']])
    def mutate(self,fn):
        m=self.act(self.a,'heartbeat').json['match'];fn(m)
        with self.store.connect() as db:db.execute('UPDATE boxing_matches SET state=? WHERE id=?',(json.dumps(m),self.mid))
    def begin(self):
        self.started=self.now
        m=self.act(self.a,'special').json['match'];self.special=m['special'];self.game=m['combat_now'];return m
    def click(self,target,client=None,**extra):
        return self.act(client or self.b,'special_aim',special_id=self.special['id'],target_id=target,**extra)
    def complete(self):
        for t in self.special['challenge']['targets']:
            self.now=t['opens_at']+.2
            self.assertEqual(self.click(t['id']).status_code,200)
        self.now=self.special['challenge']['resolve_at']+.01
        return self.act(self.a,'heartbeat').json['match']
    def test_all_targets_evade_without_damage_and_resume_exact_clock(self):
        self.begin();m=self.complete()
        self.assertEqual(m['special']['phase'],'evaded');self.assertEqual(m['players'][1]['hp'],10)
        self.assertAlmostEqual(m['combat_now']-self.game,.01)
        self.assertEqual(m['players'][0]['special_ready_at'],self.started+180)
        self.assertEqual(m['events'][-1]['damage'],0)
        self.assertEqual(self.act(self.a,'special').status_code,400)
    def test_miss_waits_then_cinematic_single_half_max_hit(self):
        self.begin();self.now=self.started+10.1
        m=self.act(self.b,'heartbeat').json['match'];self.assertEqual(m['special']['phase'],'aim')
        self.now=self.started+10.2;m=self.act(self.b,'heartbeat').json['match'];self.assertEqual(m['special']['phase'],'cinematic');self.assertEqual(m['players'][1]['hp'],10)
        self.now=self.started+14.29;m=self.act(self.b,'heartbeat').json['match'];self.assertEqual(m['players'][1]['hp'],5)
        self.assertEqual(m['players'][1]['armor'],10);self.assertAlmostEqual(m['combat_now'],self.game)
        for _ in range(3):self.assertEqual(self.act(self.a,'heartbeat').json['match']['players'][1]['hp'],5)
        self.now=self.started+16.4;m=self.act(self.a,'heartbeat').json['match'];self.assertTrue(m['special']['complete']);self.assertAlmostEqual(m['combat_now']-self.game,.02)
    def test_low_hp_ramps_and_knockout_waits_for_cutscene(self):
        self.mutate(lambda m:m['players'][1].update(hp=4));self.begin()
        targets=self.special['challenge']['targets'];self.assertTrue(self.special['challenge']['urgent']);self.assertEqual(len(targets),10)
        self.assertAlmostEqual(targets[-1]['closes_at']-targets[0]['opens_at'],10)
        self.assertGreater(targets[0]['closes_at']-targets[0]['opens_at'],targets[-1]['closes_at']-targets[-1]['opens_at'])
        self.assertEqual(self.special['damage'],5)
        self.now=self.started+14.3;m=self.act(self.b,'heartbeat').json['match'];self.assertEqual(m['players'][1]['hp'],0);self.assertEqual(m['status'],'active')
        self.now=self.started+16.4;m=self.act(self.a,'heartbeat').json['match'];self.assertEqual(m['status'],'round_break');self.assertTrue(m['knockdown']['launch'])
    def test_exact_half_hp_uses_moderate_schedule(self):
        self.mutate(lambda m:m['players'][1].update(hp=5));self.begin();self.assertFalse(self.special['challenge']['urgent']);self.assertEqual(len(self.special['challenge']['targets']),8)
    def test_forged_early_duplicate_late_and_attacker_inputs(self):
        self.begin();a,b=self.special['challenge']['targets'][:2]
        self.assertEqual(self.click(a['id'],self.a).status_code,400)
        self.click(b['id']);m=self.click('made-up').json['match'];self.assertFalse(m['special']['challenge']['targets'][1]['hit'])
        self.now=a['opens_at']+.3;self.click(a['id']);self.click(a['id']);m=self.act(self.a,'heartbeat').json['match'];self.assertEqual(sum(t['hit'] for t in m['special']['challenge']['targets']),1)
        self.now=b['closes_at']+.3;m=self.click(b['id']).json['match'];self.assertFalse(m['special']['challenge']['targets'][1]['hit'])
    def test_stray_click_fails_even_with_every_target(self):
        self.begin();self.click(None);m=self.complete();self.assertEqual(m['special']['phase'],'cinematic')
    def test_pause_with_v_and_frozen_stamina_and_inputs(self):
        self.act(self.a,'skill');self.mutate(lambda m:m['players'][1].update(stamina=5,stamina_spent_at=0));self.begin()
        self.now+=1;m=self.act(self.b,'right',99,move=1).json['match'];self.assertEqual(m['pending_strikes'],[]);self.assertEqual(m['players'][1]['stamina'],5)
        m=self.complete();self.assertAlmostEqual(m['combat_now']-self.game,.004);self.assertAlmostEqual(m['players'][1]['stamina'],5.05)
    def test_bot_reacts_on_server_and_fast_low_hp_targets_can_beat_it(self):
        import boxing_aim
        self.mutate(lambda m:m['players'][1].update(bot=True))
        self.begin();m=self.act(self.a,'heartbeat').json['match']
        boxing_aim.prepare(m,self.special['challenge']['resolve_at']+.01)
        self.assertEqual(m['special']['phase'],'evaded')
        m['players'][1]['hp']=4;m['players'][0]['special_ready_at']=0
        import boxing_special
        boxing_special.activate(m,m['players'][0],self.started+30)
        boxing_aim.prepare(m,self.started+41)
        self.assertEqual(m['special']['phase'],'cinematic')

    def test_leave_prevents_damage(self):
        self.begin();self.now+=1;self.act(self.b,'leave');self.now+=15
        m=self.act(self.a,'heartbeat').json['match'];self.assertEqual(m['status'],'finished');self.assertEqual(m['players'][1]['hp'],10)

if __name__=='__main__':unittest.main()
