"""Permanent profile HP: exponential goals, ownership, retries and combat snapshots."""
import unittest
from unittest.mock import patch
import boxing,boxing_training as training
import test_boxing as legacy

class ProgressMath(unittest.TestCase):
    def test_exact_incremental_goals(self):
        for hits,level,hp,current,goal in [(0,0,50,0,10),(9,0,50,9,10),(10,1,52,0,20),(29,1,52,19,20),(30,2,54,0,40),(69,2,54,39,40),(70,3,56,0,80),(150,4,58,0,160)]:
            p=training.progress(hits);self.assertEqual((p['level'],p['max_hp'],p['progress_hits'],p['next_goal']),(level,hp,current,goal));self.assertEqual(p['hits_to_next'],goal-current)
    def test_large_counts_do_not_overflow(self):
        p=training.progress(training.MAX_HITS);self.assertGreater(p['next_goal'],p['progress_hits']);self.assertLess(p['max_hp'],160)

class TrainingRoutes(unittest.TestCase):
    def setUp(self):
        legacy.BoxingTests.setUp(self)
        self.path='/social/boxing/training/'+str(self.pa);self.seq=0
    def start(self):
        r=self.a.post(self.path+'/start',json={});self.assertEqual(r.status_code,200,r.json);self.token=r.json['token'];self.seq=0;return r.json
    def hit(self,**extra):
        self.seq+=1;event=dict(seq=self.seq,hand='left',kind='straight',distance=1.05);event.update(extra)
        return self.a.post(self.path+'/hits',json={'token':self.token,'events':[event]})
    def train(self,n):
        for _ in range(n):self.now+=.65;self.assertEqual(self.hit().status_code,200)
        return self.a.get(self.path).json
    def test_persistence_and_incremental_upgrade_costs(self):
        self.start();self.assertEqual(self.train(10)['max_hp'],52);self.assertEqual(self.train(19)['max_hp'],52);p=self.train(1);self.assertEqual((p['max_hp'],p['next_goal'],p['progress_hits']),(54,40,0))
        self.start();self.assertEqual(self.a.get(self.path).json['total_hits'],30)
    def test_private_profiles_and_anonymous_requests(self):
        import app
        self.assertEqual(app.app.test_client().get(self.path).status_code,401)
        self.assertEqual(self.b.get(self.path).status_code,404);self.assertEqual(self.b.post(self.path+'/start',json={}).status_code,404)
        self.start();self.assertEqual(self.b.post(self.path+'/hits',json={'token':self.token,'events':[dict(seq=1,hand='left',kind='hook',distance=1)]}).status_code,404)
    def test_duplicate_lost_response_cannot_add_twice(self):
        self.start();self.now+=1;data={'token':self.token,'events':[dict(seq=1,hand='left',kind='straight',distance=1)]}
        a=self.a.post(self.path+'/hits',json=data).json;b=self.a.post(self.path+'/hits',json=data).json
        self.assertEqual((a['accepted'],b['accepted']),(1,0));self.assertEqual(b['progress']['total_hits'],1)
    def test_misses_kicks_bad_sequences_and_huge_batches_are_rejected(self):
        self.start()
        for changes in [dict(distance=2),dict(distance=-1),dict(distance=True),dict(distance=float('inf')),dict(kind='kick'),dict(hand='both'),dict(seq=True),dict(seq=-1)]:self.assertEqual(self.hit(**changes).status_code,400)
        e=dict(seq=1,hand='left',kind='hook',distance=1)
        for events in [[],[e]*17,[e,e]]:self.assertEqual(self.a.post(self.path+'/hits',json={'token':self.token,'events':events}).status_code,400)
        self.assertEqual(self.a.get(self.path).json['total_hits'],0)
    def test_shared_budget_survives_restarts_and_multitab_tokens(self):
        self.start();old=self.token;self.hit();self.start();self.assertEqual(self.hit().json['accepted'],0)
        r=self.a.post(self.path+'/hits',json={'token':old,'events':[dict(seq=2,hand='right',kind='hook',distance=1)]});self.assertEqual(r.status_code,409)
        self.now+=100;events=[dict(seq=i+2,hand='left',kind='straight',distance=1) for i in range(16)]
        r=self.a.post(self.path+'/hits',json={'token':self.token,'events':events}).json;self.assertEqual(r['accepted'],training.BURST);self.assertEqual(r['progress']['total_hits'],1+training.BURST)
    def test_expired_session_does_not_award_offline_hits(self):
        self.start();self.now+=121;self.assertEqual(self.hit().status_code,409);self.assertEqual(self.a.get(self.path).json['total_hits'],0)
    def test_real_fighter_hp_snapshot_round_reset_and_fixed_bot_hp(self):
        self.fp.stop();self.a.post('/profiles/'+str(self.pa)+'/character',json={'appearance':{}})
        self.start();self.train(10)
        r=self.a.post('/social/boxing/bot',json={'profile':self.pa,'control_mode':'computer','difficulty':'easy'});self.assertEqual(r.status_code,200,r.json);m=r.json['match'];self.assertEqual([(p['hp'],p['max_hp']) for p in m['players']],[(52,52),(20,20)])
        self.train(20);self.assertEqual(m['players'][0]['max_hp'],52)
        boxing.action(m,self.uid,{'action':'ready'},self.now);self.now=m['start'];boxing.advance(m,self.now);boxing.knockout(m,m['players'][0],self.now);m['players'][0]['seen']=self.now+10;boxing.advance(m,self.now+10)
        self.assertEqual([p['hp'] for p in m['players']],[52,20])
        self.a.post('/social/boxing/'+m['id'],json={'action':'leave'})
        r=self.a.post('/social/boxing/bot',json={'profile':self.pa,'control_mode':'computer','difficulty':'hard'});self.assertEqual(r.status_code,200,r.json);self.assertEqual([(p['hp'],p['max_hp']) for p in r.json['match']['players']],[(54,54),(50,50)])
