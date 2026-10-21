"""Health arithmetic/storage and optional voice regressions; no clinical validation."""
from datetime import date, timedelta
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, AsyncMock

from health import analyze, normalize
from leaderboard import LeaderboardStore
from voice import VoiceCache, PHRASES

BASE=dict(age=21,height_cm=170,weight_kg=70,measured_on='2026-01-01',goal='build')


class HealthCalculationTests(unittest.TestCase):
    def test_bmi_and_unknown_composition_are_distinct(self):
        a=analyze(BASE)
        self.assertEqual(a['bmi'],24.22)
        self.assertEqual(a['category_key'],'reference')
        self.assertIsNone(a['fat_mass_kg'])
        self.assertIsNone(a['lean_mass_kg'])
        self.assertIsNone(a['muscle_kg'])

    def test_measured_composition_math_does_not_estimate_muscle(self):
        a=analyze(dict(BASE,body_fat_pct=20))
        self.assertEqual(a['fat_mass_kg'],14)
        self.assertEqual(a['lean_mass_kg'],56)
        self.assertIsNone(a['muscle_kg'])
        a=analyze(dict(BASE,body_fat_pct=20,muscle_kg=31))
        self.assertEqual(a['muscle_kg'],31)
        self.assertNotEqual(a['muscle_kg'],a['lean_mass_kg'])

    def test_categories_at_boundaries_use_general_adult_standard(self):
        for bmi,key in [(18.49,'underweight'),(18.5,'reference'),(24.99,'reference'),
                        (25,'overweight'),(29.99,'overweight'),(30,'obesity')]:
            with self.subTest(bmi=bmi):
                self.assertEqual(analyze(dict(BASE,height_cm=200,weight_kg=bmi*4))['category_key'],key)

    def test_under_20_is_never_classified_with_adult_cutoffs(self):
        for age in (2,10,19):
            a=analyze(dict(BASE,age=age))
            self.assertFalse(a['adult'])
            self.assertEqual(a['category_key'],'not_adult')
        self.assertTrue(analyze(dict(BASE,age=20))['adult'])

    def test_invalid_numbers_dates_and_inconsistent_measurements_rejected(self):
        cases=[dict(BASE,height_cm=0),dict(BASE,weight_kg=True),dict(BASE,age=21.5),
               dict(BASE,body_fat_pct='nan'),dict(BASE,weight_kg=float('inf')),
               dict(BASE,muscle_kg=71),dict(BASE,body_fat_pct=50,muscle_kg=40),
               dict(BASE,measured_on='not a date'),dict(BASE,measured_on='2999-01-01'),
               dict(BASE,goal='invalid'),[],None]
        for data in cases:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):analyze(data)

    def test_form_strings_and_optional_empty_values(self):
        a=analyze(dict(BASE,age='21',height_cm='170.0',weight_kg='70',body_fat_pct='',muscle_kg=None))
        self.assertEqual(a['bmi'],24.22)
        self.assertIsNone(a['muscle_kg'])

    def test_theme_or_sex_does_not_change_bmi_formula(self):
        for theme in ('power','spicy'):
            self.assertEqual(analyze(dict(BASE,theme=theme,sex='anything'))['bmi'],24.22)


class HealthStorageTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.store=LeaderboardStore(Path(folder.name)/'fitness.db')
        self.first=self.store.create_profile('First')
        self.second=self.store.create_profile('Second')

    def test_players_have_separate_persistent_health_history(self):
        a=self.store.save_health(self.first['id'],BASE)
        self.store.save_health(self.second['id'],dict(BASE,weight_kg=80))
        restarted=LeaderboardStore(self.store.path)
        rows=restarted.health_history(self.first['id'])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['id'],a['id'])
        self.assertEqual(rows[0]['analysis']['inputs']['weight_kg'],70)
        self.assertEqual(restarted.health_history(self.second['id'])[0]['analysis']['inputs']['weight_kg'],80)

    def test_same_measurement_save_is_idempotent_and_new_date_adds_history(self):
        self.assertTrue(self.store.save_health(self.first['id'],BASE)['new_record'])
        self.assertFalse(self.store.save_health(self.first['id'],BASE)['new_record'])
        self.assertTrue(self.store.save_health(self.first['id'],dict(BASE,measured_on='2026-01-02'))['new_record'])
        records=self.store.health_history(self.first['id'])
        self.assertEqual(len(records),2)
        self.assertEqual(records[0]['analysis']['inputs']['measured_on'],'2026-01-02')

    def test_missing_player_and_invalid_save_leave_no_records(self):
        with self.assertRaises(ValueError):self.store.save_health(999,BASE)
        with self.assertRaises(ValueError):self.store.save_health(self.first['id'],dict(BASE,weight_kg=-1))
        self.assertEqual(self.store.health_history(self.first['id']),[])

    def test_old_scores_survive_additive_health_table_migration(self):
        self.store.save_set('old',self.first['id'],'curl','right',5,0,0,5,{})
        with sqlite3.connect(self.store.path) as db:db.execute('DROP TABLE health_records')
        self.store.save_health(self.first['id'],BASE)
        self.assertEqual(self.store.standings('curl','right')[0]['total'],5)
        self.assertEqual(len(self.store.health_history(self.first['id'])),1)

    def test_health_routes_validate_and_leaderboard_never_contains_health(self):
        import app
        client=app.app.test_client()
        with patch.object(app,'store',self.store):
            from test_sessions import authorize_client
            authorize_client(app,client)
            self.assertEqual(client.post('/health/analyze',json=BASE).json['analysis']['bmi'],24.22)
            self.assertEqual(client.post('/health/analyze',json=[]).status_code,400)
            path='/profiles/'+str(self.first['id'])+'/health'
            self.assertEqual(client.post(path,json=BASE).status_code,200)
            self.assertEqual(len(client.get(path).json['records']),1)
            self.assertEqual(client.get('/profiles/999/health').status_code,404)
            self.store.save_set('score',self.first['id'],'curl','right',2,0,0,2,{})
            data=client.get('/leaderboard?arm=right').json
            self.assertNotIn('height_cm',json.dumps(data))
            self.assertNotIn('weight_kg',json.dumps(data))


class NaturalVoiceTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.cache=VoiceCache(folder.name)

    def test_provider_caches_are_separate(self):
        with patch.object(self.cache,'generate',side_effect=lambda code,provider:provider.encode()*100) as generate:
            female=self.cache.audio('arm','neural_female')
            male=self.cache.audio('arm','neural_male')
            self.assertNotEqual(female,male)
            self.assertEqual(female,self.cache.audio('arm','neural_female'))
            self.assertEqual(generate.call_count,2)

    def test_neural_voices_and_stream_audio(self):
        class FakeSpeech:
            async def stream(self):
                yield {'type':'SentenceBoundary','text':'not audio'}
                yield {'type':'audio','data':b'ID3'+b'A'*200}
        with patch('edge_tts.Communicate',return_value=FakeSpeech()) as communicate:
            data=self.cache.audio('ready','neural_female')
            self.assertTrue(data.startswith(b'ID3'))
            self.assertEqual(communicate.call_args.args[1],'th-TH-PremwadeeNeural')
            self.cache.audio('ready','neural_male')
            self.assertEqual(communicate.call_args.args[1],'th-TH-NiwatNeural')

    def test_missing_openai_key_is_explicit_and_never_calls_provider(self):
        with patch.dict('os.environ',{},clear=True):
            self.assertFalse(self.cache.configuration()['openai_available'])
            with patch.object(self.cache,'generate') as generate:
                with self.assertRaises(RuntimeError):self.cache.audio('arm','openai')
                generate.assert_not_called()

    def test_openai_uses_only_fixed_phrase_and_warm_voice_instructions(self):
        payload=b'ID3'+b'A'*200
        with patch.dict('os.environ',{'OPENAI_API_KEY':'test-only-placeholder'}):
            with patch('voice.urlopen') as open_url:
                open_url.return_value.__enter__.return_value.read.return_value=payload
                self.assertEqual(self.cache.audio('arm','openai'),payload)
                request=open_url.call_args.args[0]
                body=json.loads(request.data)
                self.assertEqual(request.full_url,'https://api.openai.com/v1/audio/speech')
                self.assertEqual(body['input'],PHRASES['arm'])
                self.assertEqual(body['model'],'gpt-4o-mini-tts')
                self.assertIn('warm',body['instructions'])
                self.assertEqual(body['voice'],'coral')
                self.assertNotIn('profile',body)

    def test_neural_failure_cooldown_and_invalid_provider(self):
        with patch.object(self.cache,'neural_audio',new=AsyncMock(side_effect=TimeoutError)) as generate:
            with self.assertRaises(TimeoutError):self.cache.audio('arm','neural_female')
            with self.assertRaises(RuntimeError):self.cache.audio('arm','neural_female')
            self.assertEqual(generate.call_count,1)
        with self.assertRaises(ValueError):self.cache.audio('arm','other')

    def test_voice_routes_and_configuration_do_not_expose_key(self):
        import app
        client=app.app.test_client()
        with patch.dict('os.environ',{},clear=True):
            self.assertEqual(client.get('/speech/arm.mp3?voice=openai').status_code,409)
        self.assertEqual(client.get('/speech/arm.mp3?voice=anything').status_code,400)
        with patch.object(app.voice_cache,'audio',return_value=b'ID3'+b'A'*200) as generate:
            self.assertEqual(client.get('/speech/arm.mp3?voice=neural_male').status_code,200)
            generate.assert_called_once_with('arm','neural_male')
        with patch.dict('os.environ',{'OPENAI_API_KEY':'test-only-placeholder'}):
            page=client.get('/').data
            self.assertNotIn(b'test-only-placeholder',page)
            for element in [b'powerTheme',b'spicyTheme',b'healthPage',b'voiceSpeed']:
                self.assertIn(element,page)

if __name__=='__main__':unittest.main()
