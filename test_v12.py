"""Camera lifecycle, challenge accounting and stricter upper-arm regressions."""
import tempfile,unittest,math
from pathlib import Path
from unittest.mock import patch,MagicMock
from types import SimpleNamespace as NS
import app as server
import challenges
from leaderboard import LeaderboardStore
from sessions import SessionRegistry
from test_sessions import authorize_client
from test_v11 import landmarks
from strict_form import geometry

class ChallengeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=LeaderboardStore(Path(self.temp.name)/'db');self.p=self.store.create_profile('P')['id'];self.q=self.store.create_profile('Q')['id']
    def save(self,key,reps,exercise='curl',profile=None):
        self.store.save_set(key,profile or self.p,exercise,'right',reps,0,0,reps,{})
    def test_twenty_across_sets_duplicate_save_and_restart(self):
        a=challenges.begin(self.store,self.p)['run'];self.assertEqual(a['id'],challenges.begin(self.store,self.p)['run']['id'])
        self.save('a',12);challenges.credit(self.store,a['id'],'a',self.p);challenges.credit(self.store,a['id'],'a',self.p)
        self.assertEqual(challenges.overview(self.store,self.p)['run']['progress'],12)
        self.save('b',8)
        for _ in range(2):challenges.credit(self.store,a['id'],'b',self.p)
        d=challenges.overview(LeaderboardStore(self.store.path),self.p);self.assertEqual(d['purple_coins'],1);self.assertEqual(d['run']['progress'],20)
        b=challenges.begin(self.store,self.p)['run'];self.assertNotEqual(a['id'],b['id'])
        challenges.credit(self.store,b['id'],'a',self.p);self.assertEqual(challenges.overview(self.store,self.p)['run']['progress'],0)
    def test_other_exercise_profile_and_unsaved_attempts_do_not_count(self):
        run=challenges.begin(self.store,self.p)['run']['id']
        self.save('hammer',20,'hammer_curl');self.save('other',20,profile=self.q)
        for key in ('hammer','other','invalid-no-workout'):challenges.credit(self.store,run,key,self.p)
        self.assertEqual(challenges.overview(self.store,self.p)['run']['progress'],0)
        self.assertEqual(challenges.overview(self.store,self.p)['purple_coins'],0)
    def test_auto_pause_at_remaining_target_awards_once(self):
        run=challenges.begin(self.store,self.p)['run']['id'];self.save('first',19);challenges.credit(self.store,run,'first',self.p)
        c=server.BrowserCoach(self.store);c.state.update(running=True,profile=self.store.profile(self.p));c.challenge_id=run;c.challenge_remaining=1
        c.forms['right'].counter.reps=1;c.outputs['right']=c.forms['right'].base();c.aggregate();c.maybe_rest(5000)
        self.assertTrue(c.state['paused']);self.assertEqual(challenges.overview(self.store,self.p)['purple_coins'],1)
        c.pause();self.assertEqual(challenges.overview(self.store,self.p)['purple_coins'],1)
        c.new_set();self.assertEqual(c.challenge_remaining,0)
    def test_excess_reps_do_not_mint_multiple_coins(self):
        run=challenges.begin(self.store,self.p)['run']['id'];self.save('big',99);challenges.credit(self.store,run,'big',self.p)
        self.assertEqual(challenges.overview(self.store,self.p)['purple_coins'],1)

class SessionLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=LeaderboardStore(Path(self.tmp.name)/'db');self.reg=SessionRegistry(lambda:server.BrowserCoach(self.store))
        self.addCleanup(self.reg.stop_all)
        self.patches=[patch.object(server,'store',self.store),patch.object(server,'sessions',self.reg)]
        for p in self.patches:p.start();self.addCleanup(p.stop)
        self.client=server.app.test_client();authorize_client(server,self.client)
        self.profile=self.client.post('/profiles',json={'name':'Player'}).json['profile']
    def test_reopen_every_exercise_and_old_stop_cannot_close_new(self):
        previous=None
        import membership,time
        owner=next(iter(self.reg.items.values()))['owner']
        with self.store.connect() as db:
            membership.schema(db)
            db.execute('INSERT INTO vip_memberships(owner,expires) VALUES(?,?)',(owner,time.time()+86400))
        with patch.object(server.vision.PoseLandmarker,'create_from_options',side_effect=lambda options:MagicMock()):
            for exercise in server.CATALOG.values():
                result=self.client.post('/start',json={'exercise':exercise['id'],'arm':exercise['default_arm'],'profile_id':self.profile['id']})
                self.assertEqual(result.status_code,200,result.json)
                current=self.client.get('/status').json
                if previous:self.assertEqual(self.client.post('/stop',headers={'X-Set-ID':previous}).status_code,409)
                self.assertTrue(self.client.get('/status').json['running'])
                self.assertEqual(self.client.post('/stop',headers={'X-Set-ID':current['set_id']}).status_code,200)
                self.assertFalse(self.client.get('/status').json['running']);previous=current['set_id']
    def test_challenge_ownership_and_payload_cannot_award_currency(self):
        path=f"/profiles/{self.profile['id']}/challenges"
        b=server.app.test_client();authorize_client(server,b)
        self.assertEqual(b.post(path,json={'action':'begin'}).status_code,404)
        self.assertEqual(self.client.post(path,json={'action':'award','purple_coins':999}).status_code,400)
        self.assertEqual(self.client.post(path,json={'action':'begin','purple_coins':999}).json['purple_coins'],0)
        self.assertEqual(self.client.post(f"/profiles/{self.profile['id']}/rewards",json={'action':'redeem','item':'whey'}).status_code,403)

class UpperArmTests(unittest.TestCase):
    def test_forward_upper_arm_not_parallel_rejected(self):
        p,w=landmarks(80);e=w[14];v=(w[16].x-e.x,w[16].y-e.y,w[16].z-e.z)
        a=math.radians(55);e.y=.3*math.cos(a);e.z=-.3*math.sin(a)
        w[16]=NS(x=e.x+v[0],y=e.y+v[1],z=e.z+v[2])
        self.assertIn('upper_position',geometry('curl','right',p,w,{'lean':0})[1])
    def test_rotating_person_toward_camera_does_not_itself_fail(self):
        p,w=landmarks(80)
        for point in w:point.x,point.z=point.z,-point.x
        known,bad=geometry('curl','right',p,w,{'lean':0});self.assertTrue(known);self.assertEqual(bad,[])

if __name__=='__main__':unittest.main()
