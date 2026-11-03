"""Rule 10: finite punch budget, recovery, interruptible combat and escape."""
import unittest
from unittest.mock import patch
import boxing
import boxing_stamina as stamina
import test_boxing as fixtures


class RecoveryTests(unittest.TestCase):
    def test_budget_spam_rest_and_guard(self):
        p = {'stamina': 20, 'stamina_at': 100}
        m = {'rules': 10, 'status': 'active', 'players': [p], 'clock_wall': 100}
        for i in range(10):
            wall = 100 + i * .4
            m['clock_wall'] = wall
            stamina.advance(m, wall, wall)
            self.assertTrue(stamina.spend(m, p, 'straight'))
        self.assertEqual(p['stamina'], 0)
        self.assertFalse(stamina.spend(m, p, 'straight'))
        stamina.advance(m, 104.25, 104.25)
        self.assertAlmostEqual(p['stamina'], 0)
        stamina.advance(m, 105.25, 105.25)
        self.assertAlmostEqual(p['stamina'], 5)
        # Guard recovers immediately, even during the normal rest delay.
        m['clock_wall'] = 105.25
        stamina.spend(m, p, 'straight')
        p['guard_until'] = 106
        stamina.advance(m, 105.75, 105.75)
        self.assertAlmostEqual(p['stamina'], 5.5)
        stamina.advance(m, 120, 120)
        self.assertEqual(p['stamina'], 20)

    def test_recovery_uses_wall_time_and_pauses_in_cinematic(self):
        p = {'stamina': 0, 'stamina_at': 100, 'stamina_spent_at': 90}
        m = {'rules': 10, 'status': 'active', 'players': [p]}
        stamina.advance(m, 101, 100.4)
        self.assertEqual(p['stamina'], 5)
        m['special'] = {'complete': False}
        stamina.advance(m, 102, 100.4)
        self.assertEqual(p['stamina'], 5)
        m['special']['complete'] = True
        stamina.advance(m, 103, 100.8)
        self.assertEqual(p['stamina'], 10)


class CombatTests(unittest.TestCase):
    create = fixtures.BoxingTests.create
    act = fixtures.BoxingTests.act

    def setUp(self):
        fixtures.BoxingTests.setUp(self)
        rule = patch.object(boxing, 'MATCH_RULES', 10)
        rule.start(); self.addCleanup(rule.stop)
        self.create('computer')
        self.act(self.b, 'accept'); self.act(self.a, 'ready'); self.act(self.b, 'ready')
        self.now += 5
        self.act(self.a, 'heartbeat')

    def punch(self, client, hand, seq):
        r = self.act(client, hand, seq, strike_id=str(seq))
        self.assertEqual(r.status_code, 200, r.json)
        return r.json['match']

    def test_hit_interrupts_attack_but_guard_dash_remain_available(self):
        self.punch(self.a, 'right', 1)
        self.now += .2
        m = self.punch(self.b, 'left', 1)
        q = m['players'][1]
        self.assertEqual(q['hp'], 6)
        self.assertAlmostEqual(q['x'], 1.04)
        self.assertGreater(q['hit_stun_until'], self.now)
        self.assertEqual(q['stamina'], 20)
        self.assertEqual(m['pending_strikes'], [])
        m = self.act(self.b, 'control', 2, guard=True, dash=True, move=-1).json['match']
        self.assertGreater(m['players'][1]['guard_until'], self.now)
        self.assertGreater(m['players'][1]['dash_until'], self.now)
        self.now += .1
        m = self.act(self.a, 'heartbeat').json['match']
        self.assertGreater(m['players'][1]['x'], 1.04)

    def test_guard_drains_until_broken_and_overflow_hits_hp(self):
        for i in range(3):
            self.act(self.b, 'control', i + 1, guard=True, guard_side='right')
            self.punch(self.a, 'right', i + 1)
            self.now += .2
            m = self.act(self.b, 'heartbeat').json['match']
            self.now += .25
        q = m['players'][1]
        self.assertEqual(q['armor'], 0)
        self.assertEqual(q['hp'], 8)
        self.assertEqual(m['event']['armor_damage'], 2)
        self.assertEqual(m['event']['hp_damage'], 2)

    def test_unlanded_opposite_hand_punch_is_interrupted(self):
        self.punch(self.a, 'right', 1)
        self.now += .1
        self.punch(self.b, 'left', 1)
        self.now += .1
        m = self.act(self.a, 'heartbeat').json['match']
        self.assertEqual(m['pending_strikes'], [])
        self.now += .2
        m = self.act(self.a, 'heartbeat').json['match']
        self.assertEqual(m['players'][0]['hp'], 10)
        self.assertEqual(m['players'][1]['hp'], 6)
        self.assertLess(m['players'][1]['stamina'], 20)

    def test_matching_counter_costs_energy_but_no_damage(self):
        self.punch(self.a, 'left', 1); self.punch(self.b, 'left', 1)
        self.now += .2
        m = self.act(self.a, 'heartbeat').json['match']
        self.assertEqual(m['event']['result'], 'counter')
        self.assertEqual([p['stamina'] for p in m['players']], [18, 18])
        self.assertEqual([p['hp'] for p in m['players']], [10, 10])

    def test_new_round_restores_stamina_and_clears_stun(self):
        m = self.act(self.a, 'heartbeat').json['match']
        for p in m['players']:
            p.update(stamina=0, hit_stun_until=self.now + .48)
        boxing.knockout(m, m['players'][0], self.now)
        boxing.advance(m, self.now + 10)
        self.assertEqual(m['status'], 'active')
        self.assertEqual([p['stamina'] for p in m['players']], [20, 20])
        self.assertEqual([p['hit_stun_until'] for p in m['players']], [0, 0])

    def test_miss_spends_stamina_and_duplicate_does_not(self):
        self.act(self.b, 'control', 1, move=-1)
        self.now += .6
        m = self.punch(self.a, 'left', 1)
        self.assertEqual(m['players'][0]['stamina'], 18)
        self.now += .2
        m = self.act(self.a, 'heartbeat').json['match']
        self.assertEqual(m['event']['result'], 'miss')
        self.assertEqual(self.punch(self.a, 'left', 2)['players'][0]['stamina'], 18)


if __name__ == '__main__':
    unittest.main()
