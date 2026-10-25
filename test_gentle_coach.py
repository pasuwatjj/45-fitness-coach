"""Regression checks for gentle feedback, server-derived scores and audio fallback."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import test_form_rules as form_tests


class GentleFormTests(unittest.TestCase):
    setUp=form_tests.FormTests.setUp
    feed=form_tests.FormTests.feed
    calibrate=form_tests.FormTests.calibrate
    def test_near_correct_reps_count_without_range_nagging(self):
        self.calibrate()
        for rep in range(1,4):
            for a in (140,120,100,90,90,110,130,140,140):
                out=self.feed(a,300)
                self.assertNotIn('flexion',{f['code'] for f in out['feedback']})
                self.assertNotIn('extension',{f['code'] for f in out['feedback']})
            self.assertEqual(out['reps'],rep)
            self.assertEqual(out['flagged'],0)

    def test_tiny_jitter_never_creates_range_advice_or_reps(self):
        self.calibrate()
        for a in (160,155,158,150,156,159)*8:
            out=self.feed(a,100)
            self.assertEqual(out['feedback'],[])
        self.assertEqual(out['reps'],0)
        self.assertEqual(out['observations'],{})

    def test_shallow_oscillations_cannot_farm_counts(self):
        self.calibrate()
        for a in (160,130,96,130,96,130,96,130):out=self.feed(a,500)
        self.assertEqual(out['reps'],0)
        self.coach.reset_motion()
        for a in (130,90,130,90,130):out=self.feed(a,600)
        self.assertEqual(out['reps'],0)

    def test_warning_boundary_noise_and_gentle_clear(self):
        self.calibrate()
        for value in (24,26,23,27)*10:
            self.assertNotIn('arm',{f['code'] for f in self.feed(160,100,arm=value)['feedback']})
        self.assertIn('arm',{f['code'] for f in self.feed(160,1100,arm=30)['feedback']})
        out=self.feed(160,750,arm=19)
        self.assertNotIn('arm',{f['code'] for f in out['feedback']})
        self.assertEqual(out['observations']['arm'],1)


class SessionTests(unittest.TestCase):
    def setUp(self):
        import app
        from leaderboard import LeaderboardStore
        self.app=app
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.store=LeaderboardStore(Path(folder.name)/'fitness.db')
        self.profile=self.store.create_profile('Test Player')
        self.coach=app.CameraCoach(self.store)
        self.coach.state.update(running=True,profile=self.profile)

    def put_reps(self,count=3):
        self.coach.forms['right'].counter.reps=count
        self.coach.forms['right'].observations={'arm':1,'flexion':1}
        self.coach.outputs['right']=self.coach.forms['right'].base()
        self.coach.aggregate()

    def test_pause_stop_deduplicate_same_set(self):
        self.put_reps()
        first=self.coach.pause()
        self.coach.pause()
        self.coach.stop()
        row=self.store.standings('curl','right')[0]
        self.assertEqual((row['total'],row['sets']),(3,1))
        self.assertTrue(first['saved'])
        self.assertIn('flexion',first['observations'])
        self.assertTrue(first['tips'])

    def test_resume_new_set_and_scores_survive_restart(self):
        self.put_reps(4)
        old=self.coach.state['set_id']
        self.coach.pause()
        self.assertTrue(self.coach.resume())
        self.assertNotEqual(old,self.coach.state['set_id'])
        self.assertEqual(self.coach.state['reps'],0)
        self.put_reps(2)
        self.coach.pause()
        from leaderboard import LeaderboardStore
        row=LeaderboardStore(self.store.path).standings('curl','right')[0]
        self.assertEqual((row['total'],row['best_set'],row['sets']),(6,4,2))

    def test_paused_frame_never_changes_counters(self):
        import numpy as np
        self.put_reps()
        self.coach.pause()
        self.coach.process(np.zeros((100,100,3),dtype=np.uint8),SimpleNamespace(pose_landmarks=[]),9000)
        self.assertEqual(self.coach.state['reps'],3)
        self.assertEqual(self.coach.forms['right'].counter.reps,3)

    def test_auto_rest_only_after_count_and_no_motion(self):
        self.coach.last_activity=1000
        self.coach.maybe_rest(10000)
        self.assertFalse(self.coach.state['paused'])
        self.put_reps()
        self.coach.maybe_rest(8999)
        self.assertFalse(self.coach.state['paused'])
        self.coach.maybe_rest(9000)
        self.assertTrue(self.coach.state['paused'])
        self.assertTrue(self.coach.state['summary']['automatic'])

    def test_rank_modes_separate_and_ties_share_rank(self):
        other=self.store.create_profile('Another Player')
        for sid,p,ex,arm,reps in [('a',self.profile,'curl','right',3),('b',other,'curl','right',3),
              ('c',self.profile,'curl','left',20),('d',other,'exercise2','right',50)]:
            self.store.save_set(sid,p['id'],ex,arm,reps,0,0,reps,{})
        rows=self.store.standings('curl','right')
        self.assertEqual([r['total'] for r in rows],[3,3])
        self.assertEqual([r['rank'] for r in rows],[1,1])
        self.assertEqual(self.store.standings('curl','left')[0]['total'],20)
        self.assertEqual(self.store.standings('curl','both'),[])

    def test_save_failure_keeps_set_for_retry(self):
        self.put_reps()
        with patch.object(self.store,'save_set',side_effect=OSError('disk full')):
            self.coach.pause()
            self.assertFalse(self.coach.resume())
            self.assertFalse(self.coach.reset())
            self.assertEqual(self.coach.state['reps'],3)
        self.assertTrue(self.coach.pause()['saved'])
        self.assertTrue(self.coach.resume())

    def test_profile_validation_reuse_and_sql_safety(self):
        self.assertEqual(self.store.create_profile('  test   PLAYER  ')['id'],self.profile['id'])
        for name in (None,'','x'*31):
            with self.assertRaises(ValueError):self.store.create_profile(name)
        odd=self.store.create_profile("Robert'); DROP TABLE profiles;"[:30])
        self.assertEqual(self.store.profile(odd['id'])['name'],odd['name'])
        self.assertEqual(len(self.store.profiles()),2)

    def test_profile_routes_reject_invalid_inputs_and_use_server_scores(self):
        client=self.app.app.test_client()
        with patch.object(self.app,'store',self.store):
            from test_sessions import authorize_client
            authorize_client(self.app,client)
            existing=client.get('/profiles').json['profiles']
            result=existing[0] if existing else client.post('/profiles',json={'name':'Student'}).json['profile']
            self.assertEqual(client.post('/profiles',json={'name':''}).status_code,400)
            self.assertEqual(client.post('/start',json={'profile_id':True}).status_code,400)
            self.assertEqual(client.post('/start',json={'profile_id':99999}).status_code,404)
            self.assertEqual(client.get('/leaderboard?arm=invalid').status_code,400)
            with patch.object(self.app,'coach',self.coach):
                self.put_reps(3)
                response=client.post('/pause',json={'reps':99999,'profile_id':result['id']})
                self.assertEqual(response.status_code,200)
                rows=client.get('/leaderboard?arm=right').json['rows']
                self.assertEqual(rows[0]['total'],3)
                self.assertEqual(rows[0]['profile_id'],self.profile['id'])


class VoiceTests(unittest.TestCase):
    def test_fixed_phrase_cache_and_failure_cooldown(self):
        from voice import VoiceCache
        with tempfile.TemporaryDirectory() as folder:
            v=VoiceCache(folder)
            payload=b'ID3'+b'0'*300
            with patch('gtts.gTTS') as tts:
                tts.return_value.write_to_fp.side_effect=lambda fp:fp.write(payload)
                self.assertEqual(v.audio('arm'),payload)
                self.assertEqual(v.audio('arm'),payload)
                self.assertEqual(tts.call_count,1)
            with self.assertRaises(ValueError):v.audio('../../anything')
            with patch('gtts.gTTS',side_effect=OSError('offline')) as tts:
                with self.assertRaises(OSError):v.audio('torso')
                with self.assertRaises(RuntimeError):v.audio('torso')
                self.assertEqual(tts.call_count,1)

    def test_audio_route_success_unknown_and_offline(self):
        import app
        client=app.app.test_client()
        with patch.object(app.voice_cache,'audio',return_value=b'ID3data'):
            response=client.get('/speech/arm.mp3')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.mimetype,'audio/mpeg')
        self.assertEqual(client.get('/speech/nonexistent.mp3').status_code,404)
        with patch.object(app.voice_cache,'audio',side_effect=OSError('offline')):
            self.assertEqual(client.get('/speech/arm.mp3').status_code,503)

if __name__=='__main__':unittest.main()
