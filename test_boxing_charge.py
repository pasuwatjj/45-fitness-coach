"""Authoritative hold duration, cancellation, same-punch Counter and skill isolation."""
import unittest
from unittest.mock import patch
import boxing
import test_boxing as legacy


class ChargeTests(unittest.TestCase):
    create = legacy.BoxingTests.create
    act = legacy.BoxingTests.act

    def setUp(self):
        legacy.BoxingTests.setUp(self)
        rules = patch.object(boxing, 'MATCH_RULES', 9)
        rules.start()
        self.addCleanup(rules.stop)
        self.create('computer')
        self.act(self.b, 'accept')
        self.act(self.a, 'ready')
        self.act(self.b, 'ready')
        self.now += 5
        self.act(self.a, 'heartbeat')
        self.seq = 0

    def control(self, action='control', **data):
        self.seq += 1
        result = self.act(self.a, action, self.seq, **data)
        self.assertEqual(result.status_code, 200, result.json)
        return result.json['match']

    def hold(self, seconds=1.6):
        self.control(charge_hand='right')
        for _ in range(round(seconds / .2)):
            self.now += .2
            m = self.control(charge_hand='right')
        self.assertEqual(m['players'][1]['hp'], 10)
        self.assertEqual(m.get('pending_strikes', []), [])

    def release(self, **extra):
        self.control('right', strike_id='release', **extra)
        self.now += .4
        return self.act(self.b, 'heartbeat').json['match']

    def test_full_charge_only_hits_on_release_and_caps_at_double(self):
        self.hold(3)
        m = self.release()
        self.assertEqual(m['players'][1]['hp'], 2)
        self.assertEqual(m['event']['charge_multiplier'], 2)
        self.assertEqual(self.control('right', strike_id='release')['players'][1]['hp'], 2)

    def test_client_multiplier_cannot_increase_damage(self):
        m = self.release(charge_multiplier=999, damage=999)
        self.assertEqual(m['players'][1]['hp'], 6)

    def test_guard_cancels_charge(self):
        self.hold()
        self.control(guard=True)
        self.assertEqual(self.release()['players'][1]['hp'], 6)

    def test_stale_control_cannot_bank_charge(self):
        self.hold()
        self.now += 1
        self.assertEqual(self.release()['players'][1]['hp'], 6)

    def test_matching_regular_punch_counters_charged_punch(self):
        self.hold()
        self.control('right', strike_id='charged')
        self.act(self.b, 'right', 1, strike_id='normal')
        self.now += .4
        m = self.act(self.a, 'heartbeat').json['match']
        self.assertEqual(m['event']['result'], 'counter')
        self.assertTrue(all(p['hp'] == 10 and p['armor'] == 10 for p in m['players']))

    def test_special_cancels_charge_and_still_uses_one_arm_damage(self):
        self.hold()
        m = self.act(self.a, 'special').json['match']
        self.assertIsNone(m['players'][0]['charge_hand'])
        self.assertEqual(m['special']['damage'], 4)

    def test_charge_obeys_slow_combat_clock(self):
        self.act(self.a, 'skill')
        self.hold(1.6)
        self.control('right', strike_id='slow-charge')
        self.now += 1
        m = self.act(self.b, 'heartbeat').json['match']
        self.assertLess(m['event']['charge_multiplier'], 1.5)
        self.assertGreater(m['event']['charge_multiplier'], 1)


if __name__ == '__main__':
    unittest.main()
