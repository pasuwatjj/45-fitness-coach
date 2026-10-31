"""EXP/LV accounting from authoritative, unique saved sets (no camera accuracy claim)."""
import tempfile, unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import character, training_economy, rewards
from leaderboard import LeaderboardStore
import app as server
import test_v13 as fixtures

class ProgressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=LeaderboardStore(Path(self.tmp.name)/'db');self.p=self.store.create_profile('EXP')['id']
    def test_exact_boundaries_and_carry(self):
        for total,level,current,cost in [(0,1,0,10),(9,1,9,10),(10,2,0,100),(109,2,99,100),(110,3,0,1000),(1109,3,999,1000),(1110,4,0,10000),(1111,4,1,10000),(11110,5,0,100000)]:
            with self.subTest(total=total):
                p=character.progression(total);self.assertEqual((p['level'],p['exp'],p['next_exp']),(level,current,cost));self.assertEqual(p['remaining_exp'],cost-current)
    def save(self,key,reps,difficulty=None,exercise='curl'):
        result=self.store.save_set(key,self.p,exercise,'right',reps,0,0,reps,{},difficulty=difficulty)
        rewards.save_quality(self.store,key,self.p,exercise,'right',reps,0,0,accepted=reps)
        return result
    def growth(self):return character.growth(self.store,self.p)
    def test_mixed_difficulty_and_all_primary_groups(self):
        for key in ['beginner','pro','expert']:self.save(key,1,key)
        d=self.growth();self.assertEqual(d['parts']['arms'],character.progression(1110));self.assertEqual(d['arm_parts']['right']['total_exp'],1110)
        for group in ['chest','back','legs','shoulders']:
            exercise=next(k for k,v in character.CATALOG.items() if v['group']==group)
            self.save(group,2,'pro',exercise)
            self.assertEqual(self.growth()['parts'][group]['total_exp'],200)
    def test_retry_reopen_legacy_history_and_other_owner(self):
        self.save('legacy',3);self.save('new',2,'expert')
        for _ in range(3):self.save('new',999,'expert')
        with self.assertRaises(ValueError):self.save('new',2,'pro')
        other=self.store.create_profile('Other')['id'];self.store.save_set('other',other,'curl','right',100,0,0,100,{},difficulty='expert')
        for _ in range(3):self.assertEqual(character.growth(LeaderboardStore(self.store.path),self.p)['parts']['arms']['total_exp'],2030)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM workout_sets WHERE profile_id=?',(self.p,)).fetchone()[0],2)
            self.assertEqual(db.execute("SELECT reps FROM workout_sets WHERE id='new'").fetchone()[0],2)
    def test_zero_invalid_attempts_and_atomic_save_failure(self):
        self.assertFalse(self.save('zero',0,'expert'))
        rewards.save_quality(self.store,'bad',self.p,'curl','right',0,5,3,accepted=0)
        self.assertEqual(self.growth()['parts']['arms']['total_exp'],0)
        with patch('training_economy.credit_db',side_effect=ValueError('storage failed')):
            with self.assertRaises(ValueError):self.save('failed',2,'expert')
        self.assertEqual(self.growth()['parts']['arms']['total_exp'],0)
        self.save('valid',2,'pro');rewards.save_quality(self.store,'valid',self.p,'curl','right',2,5,3,accepted=2)
        self.assertEqual(self.growth()['parts']['arms']['total_exp'],200)
    def test_concurrent_retry_once(self):
        def save(_):return LeaderboardStore(self.store.path).save_set('same',self.p,'curl','right',3,0,0,3,{},difficulty='pro')
        with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(save,range(12)))
        rewards.save_quality(self.store,'same',self.p,'curl','right',3,0,0,accepted=3)
        self.assertEqual(self.growth()['parts']['arms']['total_exp'],300)
    def test_unverified_pending_and_mismatched_records_never_credit(self):
        self.store.save_set('pending',self.p,'curl','right',9,0,0,9,{},difficulty='expert')
        self.assertEqual(self.growth()['parts']['arms']['total_exp'],0)
        rewards.save_quality(self.store,'pending',self.p,'squat','right',9,0,0,accepted=9)
        self.assertEqual(self.growth()['parts']['arms']['total_exp'],0)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM workout_sets').fetchone()[0],1)
        # A failed quality write can be retried without duplicate EXP or coins.
        self.store.save_set('retry',self.p,'curl','right',2,0,0,2,{},difficulty='pro')
        for _ in range(3):rewards.save_quality(self.store,'retry',self.p,'curl','right',2,4,3,accepted=2)
        self.assertEqual(self.growth()['parts']['arms']['total_exp'],200)

    def test_geometry_is_level_based_bounded_and_side_specific(self):
        self.assertEqual(self.growth()['levels']['arms'],0)
        self.save('one',1);a=self.growth();self.save('two',1);b=self.growth()
        self.assertEqual(a['levels']['arms'],b['levels']['arms']) # same LV, more EXP
        self.save('expert',1,'expert');c=self.growth()
        self.assertLess(a['levels']['arms'],c['levels']['arms']);self.assertLess(c['levels']['arms'],1)
        self.assertEqual(c['arm_levels']['left'],0);self.assertGreater(c['arm_levels']['right'],0)

class ApiTests(unittest.TestCase):
    setUp=fixtures.RouteTests.setUp
    def test_authoritative_frozen_difficulty_client_amount_ignored_and_access(self):
        r=self.a.post('/start',json=dict(profile_id=self.pa,exercise='curl',arm='right',difficulty='pro',exp=999999,reps=999999));self.assertEqual(r.status_code,200)
        c=self.reg.items[self.ta]['coach'];sid=c.state['set_id']
        self.assertEqual(self.a.post('/start',json=dict(profile_id=self.pa,exercise='curl',arm='right',difficulty='expert')).status_code,409)
        c.forms['right'].counter.reps=2;c.outputs['right']=c.forms['right'].base();c.rejected=4;c.unverified=3;c.aggregate()
        for _ in range(2):
            r=self.a.post('/pause',json={'difficulty':'expert','exp':999999,'reps':99999},headers={'X-Set-ID':sid});self.assertEqual(r.status_code,200,r.json)
        d=self.a.get(f'/profiles/{self.pa}/character').json;self.assertEqual(d['growth']['parts']['arms']['total_exp'],200)
        injected=self.a.post(f'/profiles/{self.pa}/character',json={'appearance':d['appearance'],'growth':{'parts':{'arms':{'total_exp':999999}}}})
        self.assertEqual(injected.json['growth'],d['growth'])
        own=self.a.get(f'/profiles/{self.pa}/overview');self.assertEqual(own.json['growth'],d['growth'])
        self.assertEqual(self.b.get(f'/profiles/{self.pa}/overview').status_code,404)
        self.assertEqual(self.b.get(f'/social/profiles/{self.pa}/overview').status_code,403)
        public=self.b.get(f'/social/characters/{self.pa}');self.assertEqual(public.json['growth'],d['growth']);self.assertNotIn('dimensions',public.json)
        self.assertEqual(self.a.post(f'/social/sharing/{self.pa}',json={'enabled':True}).status_code,200)
        self.assertEqual(self.b.get(f'/social/profiles/{self.pa}/overview').json['growth'],d['growth'])
        self.assertEqual(self.b.post(f'/profiles/{self.pa}/character',json={'growth':{'parts':{'arms':{'total_exp':99999}}}}).status_code,404)

if __name__=='__main__':unittest.main()
