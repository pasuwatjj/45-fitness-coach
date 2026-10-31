"""Calendar state transitions and synthetic joint sequences (not camera validation)."""
import copy
from datetime import date, timedelta
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from exercises import EXERCISES, CATALOG, MOTIONS
from leaderboard import LeaderboardStore
from planner import streaks, validate_items
from motion_coach import MotionCoach
from app import CameraCoach, SETTINGS

TODAY=date(2026,10,7)  # Wednesday, in Thailand.


def item(exercise='curl',sets=2,reps=3,mode='right'):
    return dict(exercise=exercise,arm_mode=mode,target_sets=sets,target_reps=reps)


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=LeaderboardStore(Path(self.temp.name)/'fitness.db')
        self.profile=self.store.create_profile('A')
        self.other=self.store.create_profile('B')
        self.id=self.profile['id']
        self.clock=patch('planner.today_thailand',return_value=TODAY)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.addCleanup(self.temp.cleanup)

    def plan(self,items=None,day=None):
        return self.store.save_plan_day(self.id,(day or TODAY).isoformat(),items if items is not None else [item()])

    def save(self,plan,set_id='one',reps=None):
        return self.store.save_set(set_id,self.id,plan['exercise'],plan['arm_mode'],
            plan['target_reps'] if reps is None else reps,0,0,plan['target_reps'],{},plan=plan)

    def test_fifteen_exercises_three_per_group_and_leg_mode(self):
        self.assertEqual(len(EXERCISES),15)
        for g in ('back','arms','chest','shoulders','legs'):
            self.assertEqual(sum(e['group']==g for e in EXERCISES),3)
        with self.assertRaises(ValueError):validate_items([item('goblet_squat',mode='both')])

    def test_week_upload_starts_on_date_maps_weekdays_and_isolates_profiles(self):
        week={str(i):[] for i in range(7)}
        week['0']=[item('hammer_curl')]
        week['2']=[item('floor_press')]
        result=self.store.upload_week(self.id,dict(month='2026-10',start_date='2026-10-07',week=week))
        self.assertEqual(len(result['changed']),25)
        month=self.store.plan_month(self.id,'2026-10')
        self.assertEqual(len(month['days']),31)
        self.assertFalse(month['days'][5]['planned'])
        self.assertEqual(month['days'][6]['items'][0]['exercise'],'floor_press')
        self.assertEqual(month['days'][11]['items'][0]['exercise'],'hammer_curl')
        self.assertEqual(month['days'][7]['status'],'rest')
        self.assertFalse(self.store.plan_day(self.other['id'])['planned'])

    def test_leap_month_and_invalid_payload_atomic(self):
        self.assertEqual(len(self.store.plan_month(self.id,'2028-02')['days']),29)
        with self.assertRaises(ValueError):self.store.plan_month(self.id,'2028-99')
        week={str(i):[] for i in range(7)}
        week['0']=[item(sets=True)]
        with self.assertRaises(ValueError):self.store.upload_week(self.id,dict(month='2026-10',start_date='2026-10-07',week=week))
        self.assertFalse(self.store.plan_day(self.id)['planned'])
        with self.assertRaises(ValueError):self.plan([item(reps=0)])
        with self.assertRaises(ValueError):self.plan([item(exercise='fake')])
        with self.assertRaises(ValueError):self.plan(day=TODAY-timedelta(days=1))

    def test_target_short_attempt_duplicate_and_progress_survive_restart(self):
        self.plan()
        first=self.store.next_plan(self.id)
        self.assertFalse(self.save(first,'short',2)['credited'])
        self.assertEqual(self.store.next_plan(self.id)['set_number'],1)
        self.assertTrue(self.save(first,'full')['credited'])
        self.assertTrue(self.save(first,'full')['credited'])
        self.assertFalse(self.save(first,'duplicate-slot')['credited'])
        fresh=LeaderboardStore(self.store.path)
        self.assertEqual(fresh.next_plan(self.id)['set_number'],2)
        self.assertEqual(fresh.plan_day(self.id)['completed_sets'],1)
        self.assertFalse(fresh.plan_day(self.id)['complete'])
        self.assertTrue(self.save(fresh.next_plan(self.id),'two')['credited'])
        self.assertTrue(fresh.plan_day(self.id)['complete'])
        self.assertIsNone(fresh.next_plan(self.id))
        self.assertEqual(fresh.plan_month(self.id,'2026-10')['streak']['current'],1)

    def test_cannot_reuse_set_for_next_slot_or_other_profile(self):
        self.plan()
        first=self.store.next_plan(self.id)
        self.save(first)
        second=self.store.next_plan(self.id)
        self.assertFalse(self.save(second)['credited'])
        with self.assertRaises(ValueError):
            self.store.save_set('alien',self.other['id'],'curl','right',3,0,0,3,{},plan=second)
        with self.store.connect() as db:
            self.assertIsNone(db.execute("SELECT id FROM workout_sets WHERE id='alien'").fetchone())

    def test_all_items_required_and_order_preserved(self):
        self.plan([item(sets=1),item('lateral_raise',sets=1)])
        self.save(self.store.next_plan(self.id),'curl')
        self.assertFalse(self.store.plan_day(self.id)['complete'])
        nxt=self.store.next_plan(self.id)
        self.assertEqual(nxt['exercise'],'lateral_raise')
        self.save(nxt,'raise')
        self.assertTrue(self.store.plan_day(self.id)['complete'])

    def test_completed_or_partial_days_preserved_on_reupload(self):
        before=self.plan()
        self.save(self.store.next_plan(self.id),'completed-set')
        with self.assertRaises(ValueError):self.plan([])
        week={str(i):[] for i in range(7)}
        result=self.store.upload_week(self.id,dict(month='2026-10',start_date='2026-10-07',week=week))
        self.assertIn('2026-10-07',result['skipped'])
        self.assertEqual(self.store.plan_day(self.id)['items'][0]['id'],before['items'][0]['id'])
        self.assertEqual(self.store.plan_day(self.id)['completed_sets'],1)

    def test_active_day_protected_but_other_dates_editable(self):
        self.plan()
        with self.assertRaises(ValueError):self.store.save_plan_day(self.id,'2026-10-07',[],active_date='2026-10-07')
        self.store.save_plan_day(self.id,'2026-10-08',[],active_date='2026-10-07')
        self.assertEqual(self.store.plan_day(self.id,'2026-10-08')['status'],'rest')

    def test_free_play_never_credits_and_midnight_does_not_backfill(self):
        self.plan()
        self.store.save_set('free',self.id,'curl','right',100,0,0,100,{})
        self.assertEqual(self.store.plan_day(self.id)['completed_sets'],0)
        plan=self.store.next_plan(self.id)
        with patch('planner.today_thailand',return_value=TODAY+timedelta(days=1)):
            self.assertFalse(self.save(plan,'late')['credited'])
        self.assertEqual(self.store.plan_day(self.id)['completed_sets'],0)

    def test_calendar_history_preserves_old_scores_health_and_profiles(self):
        self.store.save_set('old',self.id,'curl','right',7,0,0,7,{})
        self.store.save_health(self.id,dict(age=25,height_cm=170,weight_kg=65,measured_on='2026-10-01'))
        self.plan()
        self.assertEqual(self.store.standings('curl','right')[0]['total'],7)
        self.assertEqual(len(self.store.health_history(self.id)),1)
        self.assertEqual(len(self.store.profiles()),2)

    def test_plan_session_auto_pause_next_exercise_and_end(self):
        self.plan([item(sets=1,reps=2),item('hammer_curl',sets=1,reps=1)])
        coach=CameraCoach(self.store)
        with patch('app.today_thailand',return_value=TODAY),patch('app.threading.Thread'):
            self.assertTrue(coach.start_plan(self.profile,0,10))
            self.assertEqual(coach.state['plan']['target_reps'],2)
            coach.forms['right'].counter.reps=2
            coach.outputs['right']=coach.forms['right'].base()
            coach.aggregate()
            coach.maybe_rest(100)
            self.assertTrue(coach.state['paused'])
            self.assertTrue(coach.state['summary']['plan_credited'])
            self.assertFalse(coach.reset())
            self.assertTrue(coach.resume())
            self.assertEqual(coach.state['exercise'],'hammer_curl')
            self.assertEqual(coach.state['reps'],0)
            coach.forms['right'].counter.reps=1
            coach.outputs['right']=coach.forms['right'].base()
            coach.aggregate()
            coach.maybe_rest(200)
            self.assertTrue(coach.state['plan_day']['complete'])
            with self.assertRaises(ValueError):coach.resume()
            coach.stop()


class StreakTests(unittest.TestCase):
    def test_rest_neutral_missed_breaks_today_pending_does_not_break(self):
        def day(n,done=False,rest=False):
            return dict(date=f'2026-10-{n:02}',items=[] if rest else [item()],complete=done)
        days=[day(1,True),day(2,rest=True),day(3,True),day(4,rest=True),day(5,True),day(6,rest=True),day(7),day(8,True)]
        self.assertEqual(streaks(days,TODAY),dict(current=3,best=3,completed=3,label='วันฝึกตามแผน',note='วันพักไม่เพิ่มและไม่ตัดไฟ ขาดวันฝึกที่วางแผนไว้จะเริ่มนับใหม่ในวันถัดไป'))
        after=streaks(days,date(2026,10,8))
        self.assertEqual((after['current'],after['best']),(1,3))


class MotionTests(unittest.TestCase):
    def values(self,family,angle):
        return dict(elbow=angle,lean=65 if family=='row' else 90 if family in ('chest_press','triceps') else 50 if family=='incline_press' else 0,
                    arm=90 if family in ('triceps','shoulder_press') else angle if family=='raise' else 30,joint_elbow=170,knee=170)

    def sequence(self,ex):
        f=MotionCoach(ex,SETTINGS)
        start,end,_,_,_=MOTIONS[f.family]
        start=start-10 if f.limits['increasing'] else min(175,start+10)
        end=min(175,end+5) if f.limits['increasing'] else end-10
        for t in range(0,2401,100):f.update(self.values(f.family,start),t)
        self.assertIsNotNone(f.baseline,ex)
        for t in range(2500,3501,100):f.update(self.values(f.family,start+(end-start)*(t-2500)/1000),t)
        for t in range(3600,4101,100):f.update(self.values(f.family,end),t)
        for t in range(4200,5201,100):f.update(self.values(f.family,end+(start-end)*(t-4200)/1000),t)
        for t in range(5300,5701,100):f.update(self.values(f.family,start),t)
        return f,start,end

    def test_full_cycle_for_every_new_movement_family(self):
        for ex in EXERCISES:
            if ex['family']=='curl':continue
            with self.subTest(ex=ex['id']):
                f,_,_=self.sequence(ex['id'])
                self.assertEqual(f.counter.reps,1)
                self.assertEqual(f.flagged,0)

    def test_small_jitter_and_missing_landmark_never_create_rep(self):
        for ex in ('single_row','floor_press','shoulder_press','lateral_raise','goblet_squat','rdl'):
            f,start,end=self.sequence(ex)
            before=f.counter.reps
            for t in range(5800,8000,100):f.update(self.values(f.family,start+(3 if t%200 else -3)),t)
            self.assertEqual(f.counter.reps,before)
            for t in range(8100,8500,100):f.update(self.values(f.family,end),t)
            f.unavailable(8550,'missing')
            for t in range(8600,9500,100):f.update(self.values(f.family,start),t)
            self.assertEqual(f.counter.reps,before)

    def test_initial_reference_does_not_grant_a_free_rep(self):
        f=MotionCoach('floor_press',SETTINGS)
        for t in range(0,3000,100):f.update(dict(elbow=90,lean=0,arm=50,joint_elbow=90,knee=170),t)
        self.assertIsNotNone(f.baseline)
        self.assertEqual(f.counter.reps,0)

    def test_warning_requires_hold_clears_and_still_counts(self):
        f,start,end=self.sequence('single_row')
        m=self.values(f.family,start)
        m['lean']=105
        self.assertFalse(f.update(m,6000)['feedback'])
        self.assertFalse(f.update(m,6500)['feedback'])
        self.assertTrue(f.update(m,7000)['feedback'])
        m['lean']=65
        f.update(m,7100)
        self.assertFalse(f.update(m,7800)['feedback'])


class PlannerApiTests(unittest.TestCase):
    def setUp(self):
        import app as server
        self.server=server
        self.temp=tempfile.TemporaryDirectory()
        self.store=LeaderboardStore(Path(self.temp.name)/'api.db')
        self.profile=self.store.create_profile('Calendar')
        self.coach=CameraCoach(self.store)
        self.patches=[patch.object(server,'store',self.store),patch.object(server,'coach',self.coach),
                      patch('planner.today_thailand',return_value=TODAY),patch('app.today_thailand',return_value=TODAY)]
        for p in self.patches:p.start();self.addCleanup(p.stop)
        self.addCleanup(self.temp.cleanup)
        self.client=server.app.test_client()
        from test_sessions import authorize_client
        authorize_client(server,self.client)

    def test_upload_view_start_and_no_client_completion_endpoint(self):
        url=f'/profiles/{self.profile["id"]}/calendar'
        week={str(i):[] for i in range(7)};week['2']=[item(sets=1)]
        self.assertEqual(self.client.post(url+'/week',json=dict(month='2026-10',start_date='2026-10-07',week=week)).status_code,200)
        data=self.client.get(url+'?month=2026-10').get_json()
        self.assertEqual(data['today_plan']['total_sets'],1)
        with patch('app.threading.Thread'):
            r=self.client.post('/plans/today/start',json=dict(profile_id=self.profile['id'],camera=0,tolerance=10))
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.get_json()['plan']['exercise'],'curl')
        self.assertEqual(self.client.post(url+'/day',json=dict(date='2026-10-07',items=[])).status_code,400)
        self.assertEqual(self.client.post('/plans/complete',json=dict(reps=999)).status_code,404)
        self.assertEqual(self.client.post('/plans/today/start',json=dict(profile_id=True)).status_code,400)
        self.coach.state['running']=False

    def test_new_exercise_routes_and_per_exercise_scores(self):
        with patch.object(self.coach,'start',return_value=True) as start:
            r=self.client.post('/start',json=dict(exercise='rdl',arm='right',profile_id=self.profile['id']))
            self.assertEqual(r.status_code,200)
            self.assertEqual(start.call_args.args[-1],'rdl')
            self.assertEqual(start.call_args.args[3],'full')
        self.assertEqual(self.client.post('/start',json=dict(exercise='rdl',arm='both')).status_code,400)
        self.store.save_set('row',self.profile['id'],'bent_row','both',4,0,4,4,{})
        self.assertEqual(self.client.get('/leaderboard?exercise=bent_row&arm=both').get_json()['rows'][0]['total'],4)
        self.assertEqual(self.client.get('/leaderboard?exercise=curl&arm=both').get_json()['rows'],[])



class ShareTests(unittest.TestCase):
    def setUp(self):
        import app as server
        self.server=server
        self.original=server.PUBLIC_URL
        server.PUBLIC_URL=None
        self.addCleanup(setattr,server,'PUBLIC_URL',self.original)
        self.client=server.app.test_client()

    def test_local_register_whitelist_and_keyed_link(self):
        r=self.client.post('/share/register',json={'base_url':'https://fitness-demo.trycloudflare.com'})
        self.assertEqual(r.status_code,200)
        self.assertIn('?key=',r.get_json()['share_url'])
        self.assertEqual(self.client.post('/share/register',json={'base_url':'http://attacker.example'}).status_code,400)
        self.assertEqual(self.client.get('/share/qr').status_code,200)
        self.assertEqual(self.client.post('/share/register',json={'base_url':None}).status_code,200)
        self.assertIsNone(self.client.get('/connection').get_json()['share_url'])

    def test_tunnel_loopback_never_bypasses_key_and_uses_secure_cookie(self):
        server=self.server
        server.PUBLIC_URL='https://fitness-demo.trycloudflare.com'
        c=server.app.test_client()
        # The tunnel reaches localhost but its explicit Host must remain remote.
        base='http://45-public.invalid'
        self.assertEqual(c.get('/status',base_url=base).status_code,403)
        self.assertEqual(c.get('/connection',base_url=base).status_code,403)
        r=c.get('/45-fitness-coach?key='+server.ACCESS_KEY,base_url=base)
        self.assertEqual(r.status_code,302)
        self.assertIn('Secure',r.headers['Set-Cookie'])
        self.assertIn('HttpOnly',r.headers['Set-Cookie'])
        self.assertEqual(c.get('/status',base_url=base).status_code,200)
        # Even an authenticated remote visitor cannot replace the share URL.
        self.assertEqual(c.post('/share/register',base_url=base,json={'base_url':None},headers={'Origin':server.PUBLIC_URL}).status_code,403)
        self.assertEqual(c.post('/health/analyze',base_url=base,json={},headers={'Origin':server.PUBLIC_URL}).status_code,401)
        self.assertEqual(c.post('/health/analyze',base_url=base,json={},headers={'Origin':'https://evil.example'}).status_code,403)

    def test_forwarded_localhost_is_not_a_local_operator(self):
        for headers in ({'CF-Connecting-IP':'1.2.3.4'},{'X-Forwarded-For':'1.2.3.4'},{'X-Forwarded-Proto':'https'}):
            with self.subTest(headers=headers):
                self.assertEqual(self.client.get('/status',headers=headers).status_code,403)
                self.assertEqual(self.client.post('/share/register',json={'base_url':None},headers=headers).status_code,403)

if __name__=='__main__':unittest.main()
