import unittest,json,time
from unittest.mock import patch
import test_v13 as fixtures
from test_sessions import authorize_client
from test_v18 import CardioTests,pose
import app as server
import cardio,angles,progress_analysis,membership

class TimedTests(CardioTests):
    def test_custom_timer_calories_and_separate_ranking(self):
        self.round=cardio.JumpingJackRound(self.store,self.pid,'full',lambda:self.now,duration=60,kind='timed',weight_kg=70,effort='vigorous')
        self.ready()
        for _ in range(10):self.cycle()
        active=self.round.active_seconds
        self.assertGreater(active,0);self.assertLess(active,4)
        self.now=self.round.start_at+15;self.assertFalse(self.round.snapshot()['done'])
        self.now=self.round.start_at+60;self.assertTrue(self.round.snapshot()['done'])
        self.assertEqual(cardio.ranking(self.store,'full'),[])
        row=cardio.history(self.store,self.pid)[0]
        self.assertEqual(row['duration'],60);self.assertEqual(row['reps'],10)
        self.assertAlmostEqual(row['kcal'],round(7.5*3.5*70/200*active/60,2))
        self.round.stop();self.assertEqual(len(cardio.history(self.store,self.pid)),1)
    def test_idle_hidden_gap_and_preparation_not_active_time(self):
        self.ready()
        for _ in range(10):self.hold(pose())
        self.assertEqual(self.round.active_seconds,0)
        self.hold(pose(hidden=True));self.now+=3;self.hold(pose(True))
        self.assertEqual(self.round.active_seconds,0)
    def test_upper_and_missing_weight_calories_unknown(self):
        for mode,weight in [('upper',70),('full',None)]:
            r=cardio.JumpingJackRound(self.store,self.pid,mode,weight_kg=weight)
            self.assertIsNone(r.calories())
    def test_validation(self):
        for d in [{'duration':0},{'duration':1801,'kind':'timed'},{'duration':60},{'duration':True},{'weight_kg':'nan'},{'weight_kg':-1},{'effort':'magic'}]:
            with self.assertRaises(ValueError):cardio.options(d)
        self.assertEqual(cardio.options({'kind':'timed','duration':1800})['duration'],1800)

class ProgressTests(unittest.TestCase):
    setUp=fixtures.RouteTests.setUp
    def seed(self):
        with self.store.lock,self.store.connect() as db:
            angles.schema(db)
            for i,sd in enumerate([10,10,10,5,5,5]):
                data=[dict(side='right',source='2D',metrics={'elbow':dict(samples=30,mean=110,minimum=60,maximum=160,sd=30)},completed_attempts=5,low=dict(mean=65,sd=sd),high=dict(mean=155,sd=sd))]
                db.execute('INSERT INTO set_angles(id,profile_id,exercise,day,data,created_at) VALUES(?,?,?,?,?,?)',(f's{i}',self.pa,'curl',f'2026-10-{i+1:02}',json.dumps(data),f'2026-10-{i+1:02} 10:00:00'))
    def test_progress_private_trend_and_daily_values(self):
        self.seed();r=self.a.get(f'/profiles/{self.pa}/progress');self.assertEqual(r.status_code,200)
        d=r.json;self.assertEqual(d['comparisons'][0]['trend'],'more_consistent');self.assertEqual(d['comparisons'][0]['sd_change'],-5)
        self.assertEqual(d['days'][0]['rom'],90);self.assertEqual(len(d['sets']),6)
        self.assertEqual(self.b.get(f'/profiles/{self.pa}/progress').status_code,404)
        with self.store.connect() as db:db.execute("UPDATE set_angles SET data=replace(data,'\"completed_attempts\": 5','\"completed_attempts\": 1')")
        self.assertEqual(self.a.get(f'/profiles/{self.pa}/progress').json['comparisons'][0]['trend'],'insufficient')
    def test_invalid_timer_never_starts_camera(self):
        r=self.a.post('/cardio/start',json=dict(profile_id=self.pa,kind='timed',duration=-10))
        self.assertEqual(r.status_code,400);self.assertFalse(self.reg.items[self.ta]['coach'].state['running'])
    def test_timed_options_and_ownership(self):
        r=self.a.post('/cardio/start',json=dict(profile_id=self.pa,kind='timed',duration=60,weight_kg=70))
        self.assertEqual(r.status_code,200);self.assertEqual(r.json['state']['cardio']['duration'],60)
        self.assertIsNone(r.json['state']['cardio']['preparing'])
        self.assertEqual(self.b.post('/cardio/start',json=dict(profile_id=self.pa,kind='timed',duration=60)).status_code,404)
    def test_legacy_schema_migration(self):
        with self.store.connect() as db:
            db.execute('CREATE TABLE cardio_rounds(id TEXT PRIMARY KEY,profile_id INTEGER,mode TEXT,reps INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
            db.execute('INSERT INTO cardio_rounds(id,profile_id,mode,reps) VALUES(?,?,?,?)',('old',self.pa,'full',10))
        row=cardio.history(self.store,self.pa)[0]
        self.assertEqual(row['duration'],15);self.assertIsNone(row['kcal']);self.assertEqual(cardio.ranking(self.store,'full')[0]['best'],10)
    def test_8_users_200_open_close_cycles_each(self):
        clients=[(self.a,self.ta,self.pa),(self.b,self.tb,self.pb)]
        for i in range(6):
            c=server.app.test_client();token=authorize_client(server,c);pid=c.post('/profiles',json={'name':'stress'+str(i)}).json['profile']['id'];clients.append((c,token,pid))
        with self.store.connect() as db:
            membership.schema(db)
            for _,token,_ in clients:db.execute('INSERT INTO vip_memberships VALUES(?,?)',(self.reg.items[token]['owner'],time.time()+86400))
        detectors={};exercises=list(server.CATALOG)
        for i in range(200):
            for c,token,pid in clients:
                ex=exercises[i%len(exercises)]
                response=c.post('/start',json=dict(profile_id=pid,exercise=ex,arm=server.CATALOG[ex]['default_arm'],grip_enabled=False))
                self.assertEqual(response.status_code,200,response.json)
                coach=self.reg.items[token]['coach'];detectors.setdefault(token,coach.detector);self.assertIs(coach.detector,detectors[token])
            self.assertEqual(len({id(v) for v in detectors.values()}),8)
            for j,(c,token,pid) in enumerate(clients):
                sid=self.reg.items[token]['coach'].state['set_id']
                self.assertEqual(c.post('/stop',headers={'X-Set-ID':sid}).status_code,200)
                for _,other,_ in clients[j+1:]:self.assertTrue(self.reg.items[other]['coach'].state['running'])
        self.assertTrue(all(not self.reg.items[t]['coach'].state['running'] for _,t,_ in clients))

if __name__=='__main__':unittest.main()
