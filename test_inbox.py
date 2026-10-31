import unittest,copy,uuid
from datetime import datetime,timezone
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import app as server
import inbox_features as inbox
import test_v13 as fixtures
from leaderboard import LeaderboardStore

def epoch(value):return datetime.fromisoformat(value).timestamp()
class InboxTests(unittest.TestCase):
    def setUp(self):
        fixtures.RouteTests.setUp(self)
        self.now=epoch('2026-11-02T10:00:00+00:00') # Monday 17:00 Bangkok
        self.addCleanup(patch.stopall)
        patch('inbox_features.clock',side_effect=lambda:self.now).start()
        self.uid=int(self.owner.split(':')[1]);self.other=int(self.reg.items[self.tb]['owner'].split(':')[1])
    def settings(self,client=None,**changes):
        data=inbox.defaults();data['enabled']=True;data.update(changes);r=(client or self.a).post('/social/inbox/reminders',json=data);self.assertEqual(r.status_code,200,r.json);return data
    def box(self,client=None):
        r=(client or self.a).get('/social/inbox');self.assertEqual(r.status_code,200,r.json);return r.json
    def test_defaults_private_and_guest_denied(self):
        self.assertFalse(self.box()['settings']['enabled']);self.assertEqual(self.box()['unread'],0)
        self.assertEqual(server.app.test_client().get('/social/inbox').status_code,401)
        self.settings();self.assertFalse(self.box(self.b)['settings']['enabled'])
        self.assertIn('no-store',self.a.get('/social/inbox').headers['Cache-Control'])
    def test_exact_due_once_and_persists_after_store_reopen(self):
        self.settings();self.now=epoch('2026-11-02T10:59:59+00:00');self.assertEqual(self.box()['unread'],0)
        self.now+=1;first=self.box();self.assertEqual(first['unread'],1);self.assertEqual(first['messages'][0]['scheduled'],self.now)
        for _ in range(3):self.assertEqual(self.box()['unread'],1)
        with patch.object(server,'store',LeaderboardStore(self.store.path)):self.assertEqual(self.box()['messages'],first['messages'])
    def test_daily_times_disabled_day_and_offline_catchup(self):
        data=inbox.defaults();data['enabled']=True;data['days'][1]['enabled']=False;data['days'][2]['time']='20:15';self.settings(**data)
        self.now=epoch('2026-11-04T13:15:00+00:00');d=self.box();self.assertEqual(len(d['messages']),2);self.assertEqual(d['messages'][0]['scheduled'],self.now)
    def test_read_cursor_does_not_consume_newer_or_other_account(self):
        self.settings();self.settings(self.b);self.now+=3600;old=self.box()['messages'][0]['id'];other=self.box(self.b)['messages'][0]['id'];self.now+=86400;self.assertEqual(self.box()['unread'],2)
        self.assertEqual(self.a.post('/social/inbox/read',json={'source':'system','through':other}).status_code,404)
        self.assertEqual(self.a.post('/social/inbox/read',json={'source':'system','through':old}).status_code,200);self.assertEqual(self.box()['unread'],1)
        latest=self.box()['messages'][0]['id'];self.a.post('/social/inbox/read',json={'source':'system','through':latest});self.a.post('/social/inbox/read',json={'source':'system','through':old});self.assertEqual(self.box()['unread'],0);self.assertEqual(self.box(self.b)['unread'],2)
    def test_disable_preserves_due_history_and_stops_future(self):
        self.settings();self.now+=7200;self.settings(enabled=False);self.now+=3*86400;self.assertEqual(self.box()['unread'],1)
    def test_edits_do_not_backfill_or_duplicate_today(self):
        self.settings();self.now+=3600;self.assertEqual(self.box()['unread'],1)
        data=inbox.defaults();data['days'][0]['time']='19:00';self.settings(days=data['days']);self.now+=3600;self.assertEqual(self.box()['unread'],1)
        self.settings(self.b);self.assertEqual(self.box(self.b)['unread'],0)
    def test_invalid_input_is_atomic(self):
        original=self.settings()
        for field,value in [('enabled',1),('timezone','Mars/Nowhere'),('days',[]),('days',[{'day':i,'enabled':True,'time':'25:00'} for i in range(7)])]:
            bad=copy.deepcopy(original);bad[field]=value;self.assertEqual(self.a.post('/social/inbox/reminders',json=bad).status_code,400)
        self.assertEqual(self.a.get('/social/inbox/reminders').json,original)
        self.assertEqual(self.a.post('/social/inbox/reminders',json=[]).status_code,400)
    def test_concurrent_materialization_exactly_once(self):
        self.settings();self.now+=3600
        def run(_):
            store=LeaderboardStore(self.store.path)
            with store.connect() as db:db.execute('BEGIN IMMEDIATE');inbox.materialize(db,self.uid,self.now)
        with ThreadPoolExecutor(max_workers=5) as pool:list(pool.map(run,range(8)))
        self.assertEqual(self.box()['unread'],1)
    def test_friend_threads_unread_read_and_permission(self):
        self.a.post('/social/friends',json={'action':'request','account_id':self.other});self.b.post('/social/friends',json={'action':'accept','account_id':self.uid})
        response=self.b.post(f'/social/chat/{self.uid}',json={'body':'<script>alert(1)</script> hello','client_id':str(uuid.uuid4())});self.assertEqual(response.status_code,200)
        received=response.json['messages'][-1]['id'];d=self.box();self.assertEqual(d['unread'],1);self.assertEqual(d['friends'][0]['name'],'B')
        self.assertEqual(self.a.get(f'/social/chat/{self.other}').status_code,200);self.assertEqual(self.box()['unread'],1)
        self.a.post('/social/inbox/read',json={'source':'friend','account_id':self.other,'through':received});self.assertEqual(self.box()['unread'],0)
        self.assertEqual(self.b.post('/social/inbox/read',json={'source':'friend','account_id':self.uid,'through':received}).status_code,404)
        self.a.post('/social/friends',json={'action':'remove','account_id':self.other});self.assertEqual(self.box()['friends'],[])
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM friend_messages').fetchone()[0],1)
    def test_dst_overlap_delivers_only_once(self):
        self.now=epoch('2026-11-01T04:00:00+00:00');data=inbox.defaults();data['days'][6]['time']='01:30';self.settings(timezone='America/New_York',days=data['days']);self.now=epoch('2026-11-01T05:30:00+00:00');self.assertEqual(self.box()['unread'],1);self.now+=3600;self.assertEqual(self.box()['unread'],1)
    def test_dst_gap_normalizes_to_next_valid_time(self):
        self.now=epoch('2027-03-14T05:00:00+00:00');data=inbox.defaults();data['days'][6]['time']='02:30';self.settings(timezone='America/New_York',days=data['days']);self.now=epoch('2027-03-14T07:30:00+00:00');self.assertEqual(self.box()['unread'],1)
    def test_read_payload_validation(self):
        for data in [None,[],{'source':'system','through':True},{'source':'system','through':-1}]:self.assertEqual(self.a.post('/social/inbox/read',json=data).status_code,400)
