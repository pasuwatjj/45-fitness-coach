"""Focused tests using minimal original-store interfaces, not a full app test."""
import unittest, tempfile, sqlite3, threading, sys, types, math
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault('exercises',types.SimpleNamespace(CATALOG={}))
sys.modules.setdefault('training_economy',types.SimpleNamespace(schema=lambda db:db.execute('CREATE TABLE IF NOT EXISTS training_sets(set_id TEXT,profile_id INTEGER,difficulty TEXT)')))
def number(data,key,label,minimum,maximum):
    value=float(data[key])
    if not math.isfinite(value) or not minimum<=value<=maximum:raise ValueError(label)
    return value
sys.modules.setdefault('health',types.SimpleNamespace(number=number))
import character,activity_energy as energy
class Store:
    def __init__(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.db';self.lock=threading.RLock()
        with self.connect() as db:
            db.executescript('''CREATE TABLE profiles(id INTEGER PRIMARY KEY,name TEXT);INSERT INTO profiles VALUES(1,'Test'),(2,'Other');
            CREATE TABLE profile_owners(profile_id INTEGER,owner TEXT);INSERT INTO profile_owners VALUES(1,'account:1'),(2,'account:2');
            CREATE TABLE health_records(profile_id INTEGER,measured_on TEXT,created_at TEXT,inputs TEXT);
            CREATE TABLE workout_sets(id TEXT,profile_id INTEGER,exercise TEXT,reps INTEGER,left_reps INTEGER,right_reps INTEGER);''')
        character.sync_dimensions(self,1,dict(height_cm=175,weight_kg=70))
    def connect(self):
        db=sqlite3.connect(self.path);db.row_factory=sqlite3.Row;return db
    def profile(self,pid):return dict(id=pid,name='Test')
    def close(self):self.tmp.cleanup()
def pose(offset=0):
    p=[types.SimpleNamespace(x=.5,y=.5,visibility=1) for _ in range(33)]
    p[15].y+=offset;p[16].y-=offset
    return p
class EnergyTests(unittest.TestCase):
    def setUp(self):self.store=Store();self.meter=energy.ActivityMeter(self.store);self.wall=datetime(2026,10,29,12,tzinfo=energy.TH).timestamp()
    def tearDown(self):self.store.close()
    def tick(self,n,offset,**kw):self.meter.tick(1,'set1','resistance','curl',pose(offset),now=n,wall=self.wall+n,**kw)
    def test_formula(self):
        gross,active=energy.kcal(3.5,70,600);self.assertAlmostEqual(gross,42.875);self.assertAlmostEqual(active,30.625)
    def test_idempotent_retry(self):
        self.tick(0,0);self.tick(.5,.05);self.meter.flush();self.meter.flush()
        s=energy.summary(self.store,1,'2026-10-29');self.assertEqual(s['tracked_seconds'],.5)
    def test_paused_no_credit(self):
        self.tick(0,0);self.tick(.5,.05,enabled=False);self.tick(1,.1);self.meter.flush()
        self.assertEqual(energy.summary(self.store,1,'2026-10-29')['tracked_seconds'],0)
    def test_stationary_and_camera_translation_not_credit(self):
        self.tick(0,0);self.tick(.5,0)
        p=pose(0)
        for point in p:point.y+=.05
        self.meter.tick(1,'set1','resistance','curl',p,now=1,wall=self.wall+1);self.meter.flush()
        self.assertEqual(energy.summary(self.store,1,'2026-10-29')['tracked_seconds'],0)
    def test_tracking_gap(self):
        self.tick(0,0);self.tick(8,.3);self.meter.flush();self.assertFalse(self.meter.rows)
    def test_occlusion(self):
        self.tick(0,0);p=pose(.05)
        for point in p:point.visibility=.1
        self.meter.tick(1,'set1','resistance','curl',p,now=.5,wall=self.wall+.5);self.assertFalse(self.meter.rows)
    def test_midnight_split(self):
        self.wall=datetime(2026,10,29,23,59,59,750000,tzinfo=energy.TH).timestamp()
        self.tick(0,0);self.tick(.5,.05);self.meter.flush();self.assertAlmostEqual(self.meter.rows['2026-10-29'],.25);self.assertAlmostEqual(self.meter.rows['2026-10-30'],.25)
    def test_profile_isolation(self):
        self.tick(0,0);self.tick(.5,.05);self.meter.flush();self.assertEqual(energy.summary(self.store,2,'2026-10-29')['tracked_seconds'],0)
    def test_missing_weight_not_invented(self):
        m=energy.ActivityMeter(self.store)
        for n,d in [(0,0),(.5,.05)]:m.tick(2,'s','cardio','full',pose(d),now=n,wall=self.wall+n)
        m.flush();s=energy.summary(self.store,2,'2026-10-29');self.assertEqual(s['missing_weight_seconds'],.5);self.assertEqual(s['gross_kcal'],0)
    def test_weight_snapshot(self):
        self.tick(0,0);character.sync_dimensions(self.store,1,dict(height_cm=175,weight_kg=100));self.tick(.5,.05);self.meter.flush()
        self.assertEqual(energy.summary(self.store,1,'2026-10-29')['rows'][0]['weight_kg'],70)
    def test_all_activity_categories(self):
        for exercise in ['curl','row','squat','bench_press','lateral_raise']:
            for n,d in [(0,0),(.5,.05)]:self.meter.tick(1,exercise,'resistance',exercise,pose(d),now=n,wall=self.wall+n)
        for mode in ['full','upper','pushup']:
            for n,d in [(0,0),(.5,.05)]:self.meter.tick(1,mode,'cardio',mode,pose(d),now=n,wall=self.wall+n)
        self.meter.flush();s=energy.summary(self.store,1,'2026-10-29');self.assertEqual(len(s['rows']),8);self.assertEqual(s['tracked_seconds'],4)
    def test_delete_profile_cleans_energy(self):
        self.tick(0,0);self.tick(.5,.05);self.meter.flush()
        with self.store.connect() as db:db.execute('DELETE FROM profiles WHERE id=1')
        self.assertEqual(energy.summary(self.store,1,'2026-10-29')['tracked_seconds'],0)
    def test_invalid_date(self):
        with self.assertRaises(ValueError):energy.summary(self.store,1,'not-a-date')
class CharacterTests(unittest.TestCase):
    def setUp(self):self.store=Store()
    def tearDown(self):self.store.close()
    def test_legacy_defaults(self):
        old={k:v for k,v in character.DEFAULT.items() if k in ('gender','hair','hair_color','skin_color','shorts_color')}
        m=character.save(self.store,'account:1',1,{'appearance':old});self.assertEqual(m['appearance']['eyes'],'almond')
    def test_roundtrip_details(self):
        a={**character.DEFAULT,'eyes':'round','nose':'broad','face':'angular','build':.9,'eye_color':'#225588'}
        character.save(self.store,'account:1',1,{'appearance':a});self.assertEqual(character.overview(self.store,1)['appearance'],a)
    def test_wrong_owner(self):
        with self.assertRaises(PermissionError):character.save(self.store,'account:2',1,{'appearance':character.DEFAULT})
    def test_invalid_options(self):
        for key,value in [('eyes','bad'),('nose','bad'),('build',float('nan')),('build',True),('eye_color','script')]:
            with self.assertRaises(ValueError):character.save(self.store,'account:1',1,{'appearance':{**character.DEFAULT,key:value}})
    def test_weight_changes_shape_not_muscle(self):
        a=character.overview(self.store,1)
        character.sync_dimensions(self.store,1,dict(height_cm=175,weight_kg=110));b=character.overview(self.store,1)
        self.assertGreater(b['visual']['fullness'],a['visual']['fullness']);self.assertEqual(a['appearance']['build'],b['appearance']['build'])
    def test_no_private_dimensions_in_public_model(self):self.assertNotIn('dimensions',character.overview(self.store,1))
if __name__=='__main__':unittest.main()
