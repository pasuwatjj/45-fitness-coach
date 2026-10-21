import unittest
from curl_counter import CurlCounter
from exercises import CATALOG
from voice import PHRASES

class MobileRelease(unittest.TestCase):
    def test_fast_complete_path_counts_without_endpoint_dwell(self):
        c=CurlCounter()
        for t,a in [(0,150),(140,150),(190,110),(240,75),(290,110),(340,150)]:
            c.update(a,t,130,85,45)
        self.assertEqual(c.reps,1)

    def test_threshold_noise_does_not_count(self):
        c=CurlCounter()
        for t in range(0,2000,30):c.update(84 if t%60 else 86,t,130,85,45)
        self.assertEqual(c.reps,0)

    def test_instruction_matches_device_and_online_voice(self):
        for key in ('curl','hammer_curl'):
            self.assertEqual(PHRASES['teach_'+key],CATALOG[key]['teaching'])
            self.assertIn('นิ้วโป้ง',PHRASES['teach_'+key])

if __name__=='__main__':unittest.main()
