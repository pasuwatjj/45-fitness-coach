"""Shared slow clock, real-time skill limits, earned belts and consented rematches."""
import copy,json,unittest
from unittest.mock import patch
import boxing,boxing_time
import test_boxing as legacy

class SkillRematch(unittest.TestCase):
    def setUp(self):
        legacy.BoxingTests.setUp(self)
        p=patch.object(boxing,'MATCH_RULES',9);p.start();self.addCleanup(p.stop)
    create=legacy.BoxingTests.create
    act=legacy.BoxingTests.act
    def start(self):
        self.create('computer');self.act(self.b,'accept');self.act(self.a,'ready');self.act(self.b,'ready');self.now+=5;return self.act(self.a,'heartbeat').json['match']
    def keepalive(self,seconds):
        while seconds>0:
            step=min(10,seconds);self.now+=step;seconds-=step
            self.act(self.a,'heartbeat');self.act(self.b,'heartbeat')
    def end(self):
        self.act(self.b,'leave');return self.act(self.a,'heartbeat').json['match']
    def test_out_of_order_request_times_never_advance_twice(self):
        m=dict(status='active',clock_wall=1000,combat_now=1000,slow_until=1060)
        boxing_time.sync(m,1001);boxing_time.sync(m,1000.8);boxing_time.sync(m,1002)
        self.assertAlmostEqual(m['combat_now'],1000.8);self.assertEqual(m['clock_wall'],1002)
    def dodge(self):
        self.start();self.act(self.b,'control',1,slip=-.8);self.act(self.a,'left',1,strike_id='evade-me');self.now+=.2
        return self.act(self.b,'control',2,slip=-.8).json['match']
    def test_successful_lean_slows_only_attacker_and_counter_cancels(self):
        m=self.dodge();self.assertEqual(m['event']['result'],'dodge');self.assertEqual(m['players'][0]['evade_slow_until'],self.now+5);self.assertNotIn('evade_slow_until',m['players'][1])
        self.act(self.a,'control',2,move=-1);self.act(self.b,'control',3,move=-1);before=self.act(self.a,'heartbeat').json['match'];self.now+=.5;m=self.act(self.a,'heartbeat').json['match']
        self.assertAlmostEqual(before['players'][0]['x']-m['players'][0]['x'],.21,places=5);self.assertAlmostEqual(m['players'][1]['x']-before['players'][1]['x'],.525,places=5)
        m=self.act(self.b,'right',4,strike_id='counter-now').json['match'];self.assertEqual(m['players'][0]['evade_slow_until'],0);self.assertTrue(m['pending_strikes'][-1]['counter'])
    def test_dodge_slow_expires_in_five_real_seconds_without_counter(self):
        m=self.dodge();deadline=m['players'][0]['evade_slow_until'];self.now+=4.9;m=self.act(self.a,'heartbeat').json['match'];self.assertLess(self.now,deadline);self.assertEqual(m['players'][0]['motion_scale'],.4)
        self.now+=.2;self.act(self.a,'heartbeat');self.now+=.1;m=self.act(self.a,'heartbeat').json['match'];self.assertGreater(self.now,deadline);self.assertEqual(m['players'][0]['motion_scale'],1)
    def test_shared_slow_movement_and_delayed_damage(self):
        self.start();m=self.act(self.a,'skill').json['match'];self.assertEqual(m['time_scale'],.4);self.assertEqual(m['slow_until'],self.now+60)
        self.act(self.a,'left',1,strike_id='slow-left');self.now+=.2
        self.assertEqual(self.act(self.b,'heartbeat').json['match']['players'][1]['hp'],10)
        self.now+=.26;self.assertEqual(self.act(self.b,'heartbeat').json['match']['players'][1]['hp'],8)
        self.act(self.a,'control',2,move=-1);self.act(self.b,'control',1,move=-1)
        before=self.act(self.a,'heartbeat').json['match'];self.now+=.5;m=self.act(self.a,'heartbeat').json['match']
        self.assertAlmostEqual(before['players'][0]['x']-m['players'][0]['x'],.21,places=6)
        self.assertAlmostEqual(m['players'][1]['x']-before['players'][1]['x'],.21,places=6)
    def test_knockout_control_packet_commits_round_transition(self):
        m=self.start();m['players'][1]['hp']=2
        with self.store.connect() as db:db.execute('UPDATE boxing_matches SET state=? WHERE id=?',(json.dumps(m),self.mid))
        self.act(self.a,'skill');self.act(self.a,'left',1,strike_id='ko-in-flight');self.now+=.5
        r=self.act(self.a,'control',2);self.assertEqual(r.status_code,200,r.json);self.assertEqual(r.json['match']['status'],'round_break')
        self.assertEqual(self.act(self.b,'control',1).json['match']['players'][0]['wins'],1)
    def test_duration_cooldown_no_stacking_and_wall_disconnect(self):
        self.start();start=self.now;game=self.act(self.a,'skill').json['match']['combat_now']
        self.assertEqual(self.act(self.b,'skill').status_code,400)
        self.keepalive(60);m=self.act(self.a,'heartbeat').json['match'];self.assertEqual(m['time_scale'],1);self.assertAlmostEqual(m['combat_now']-game,24)
        self.assertEqual(self.act(self.a,'skill').status_code,400)
        self.keepalive(119.9);self.assertEqual(self.act(self.a,'skill').status_code,400)
        self.keepalive(.1);self.assertEqual(self.act(self.a,'skill').status_code,200)
        self.now+=21;self.act(self.a,'heartbeat');m=self.act(self.a,'heartbeat').json['match'];self.assertEqual(m['result'],'disconnect')
    def test_rematch_requires_both_can_cancel_and_is_idempotent(self):
        self.start();old=self.mid;self.end()
        m=self.act(self.a,'rematch').json['match'];self.assertEqual(m['rematch_votes'],[self.uid]);self.assertNotIn('rematch_id',m)
        self.assertEqual(self.act(self.a,'rematch_cancel').json['match']['rematch_votes'],[])
        self.act(self.b,'rematch');new=self.act(self.a,'rematch').json['match'];self.assertNotEqual(new['id'],old);self.assertEqual(new['status'],'lobby');self.assertEqual([p['wins'] for p in new['players']],[0,0]);self.assertTrue(all(not p['ready'] for p in new['players']))
        self.assertEqual(self.act(self.b,'heartbeat').json['match']['id'],new['id'])
        self.assertEqual(self.act(self.a,'rematch').json['match']['id'],new['id'])
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM boxing_matches').fetchone()[0],2)
        self.mid=new['id'];self.act(self.a,'ready');self.act(self.b,'ready');self.now+=5;self.act(self.a,'heartbeat');self.end()
        self.assertEqual(self.a.get('/social/boxing/belts/'+str(self.pa)).json['belts'],2)
    def test_active_match_rejects_rematch_and_finished_rejects_skill(self):
        self.start();self.assertEqual(self.act(self.a,'rematch').status_code,409)
        self.end();self.assertNotIn('slow_until',self.act(self.a,'skill').json['match'])
    def test_custom_room_victories_backfill_once_for_winner_profile(self):
        m=self.start();m.update(rules=8,custom_settings=dict(hp=50,armor=10,level=3));boxing.finish(m,self.other,'best_of_three',self.now)
        m['players'][1]['profile_id']=self.pb
        with self.store.connect() as db:db.execute('UPDATE boxing_matches SET state=?,updated=? WHERE id=?',(json.dumps(m),self.now-5000,self.mid))
        path='/social/boxing/belts/'+str(self.pb)
        self.assertEqual(self.b.get(path).json['belts'],1);self.assertEqual(self.b.get(path).json['belts'],1)
        self.assertEqual(self.a.get(path).status_code,404)
        self.assertEqual(self.a.get('/social/boxing/belts/'+str(self.pa)).json['belts'],0)
    def test_rematch_keeps_custom_stats_and_rejects_busy_player(self):
        m=self.start();m['custom_settings']=dict(hp=120,armor=25,level=6)
        for p in m['players']:boxing.apply_room_settings(p,m['custom_settings'])
        boxing.finish(m,self.uid,'best_of_three',self.now)
        with self.store.connect() as db:db.execute('UPDATE boxing_matches SET state=? WHERE id=?',(json.dumps(m),self.mid))
        self.act(self.a,'rematch');new=self.act(self.b,'rematch').json['match']
        self.assertEqual(new['custom_settings'],m['custom_settings']);self.assertTrue(all(p['hp']==120 and p['armor']==25 and p['damage']['left']==6 for p in new['players']))
        self.mid=new['id'];self.act(self.a,'ready');self.act(self.b,'ready');self.now+=5;self.act(self.a,'heartbeat');self.end();self.act(self.a,'rematch')
        self.assertEqual(self.b.post('/social/boxing/bot',json={'profile':self.pb,'difficulty':'easy','control_mode':'computer'}).status_code,200)
        self.assertEqual(self.act(self.b,'rematch').status_code,409)

if __name__=='__main__':unittest.main()
