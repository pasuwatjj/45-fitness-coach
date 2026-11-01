"""Only the decisive, server-confirmed hit schedules a visual finale."""
import json, unittest
from unittest.mock import patch
import boxing
import test_boxing as legacy

class FinaleTests(unittest.TestCase):
    create=legacy.BoxingTests.create
    act=legacy.BoxingTests.act
    def setUp(self):
        legacy.BoxingTests.setUp(self)
        self.input_source="keyboard"
        p=patch.object(boxing,'MATCH_RULES',9);p.start();self.addCleanup(p.stop)
    def start(self,bot=False,final=True):
        if bot:
            r=self.a.post('/social/boxing/bot',json={'profile':self.pa,'difficulty':'easy','control_mode':'computer'})
            self.assertEqual(r.status_code,200,r.json);self.mid=r.json['match']['id'];self.act(self.a,'ready')
        else:
            self.create('computer');self.act(self.b,'accept');self.act(self.a,'ready');self.act(self.b,'ready')
        self.now+=5;m=self.act(self.a,'heartbeat').json['match']
        m['players'][0]['wins']=1 if final else 0;m['players'][1].update(hp=2,slip=0,bend=0,crouch=0,guard_until=0,move=0,side=0)
        m['round']=2 if final else 1
        if bot:m['brain'].update(next_tick=self.now+100,next_attack=self.now+100)
        with self.store.connect() as db:db.execute('UPDATE boxing_matches SET state=? WHERE id=?',(json.dumps(m),self.mid))
        return m
    def hit(self,slow=False):
        if slow:self.act(self.a,'skill')
        self.act(self.a,'left',1,strike_id='deciding-hit');self.now+=.5
        return self.act(self.a,'heartbeat').json['match']
    def test_nonfinal_knockdown_keeps_ten_second_recovery(self):
        self.start(final=False);m=self.hit();self.assertNotIn('finale',m)
        self.assertEqual(m['next_round_at']-m['round_ended_at'],10)
    def test_final_hit_shared_timeline_no_extra_damage_and_one_friend_belt(self):
        self.start();m=self.hit(slow=True);f=m['finale']
        self.assertEqual((f['winner'],f['target'],f['hand']),(self.uid,self.other,'left'))
        self.assertEqual(f['started_at'],self.now);self.assertEqual(f['id'],str(m['event']['id']))
        self.assertEqual(m['players'][1]['hp'],0);self.assertEqual(m['pending_strikes'],[])
        self.assertEqual(m['next_round_at']-m['round_ended_at'],6)
        before=len(m['events']);self.act(self.a,'right',2,strike_id='during-cutscene')
        self.now+=5.99;m=self.act(self.b,'heartbeat').json['match']
        self.assertEqual(m['status'],'round_break');self.assertEqual(m['finale'],f);self.assertEqual(len(m['events']),before)
        self.assertFalse(m.get('belt_awarded'));self.now+=.02
        for _ in range(2):m=self.act(self.a,'heartbeat').json['match']
        self.assertEqual(m['status'],'finished');self.assertEqual(m['winner'],self.uid)
        self.assertEqual(self.a.get('/social/boxing/belts/'+str(self.pa)).json['belts'],1)
    def test_bot_victory_has_finale_without_profile_reward(self):
        self.start(bot=True);m=self.hit();self.assertIn('finale',m);self.now+=6.1
        m=self.act(self.a,'heartbeat').json['match'];self.assertEqual(m['status'],'finished')
        self.assertEqual(m['winner'],self.uid);self.assertFalse(m.get('belt_awarded'))
        self.assertEqual(self.a.get('/social/boxing/belts/'+str(self.pa)).json['belts'],0)
    def test_bot_can_win_the_same_finale_and_leaving_does_not_fake_a_hit(self):
        m=self.start(bot=True);bot=m['players'][1];bot['wins']=1;m['players'][0]['hp']=0
        m['event']=dict(id=91,attacker=bot['uid'],target=self.uid,result='hit',hand='right',punch_type='straight')
        boxing.knockout(m,bot,self.now);self.assertEqual(m['finale']['winner'],bot['uid'])
        boxing.finish(m,self.uid,'leave',self.now);self.assertEqual(m['winner'],bot['uid'])
        m.pop('finale');m['status']='active';boxing.finish(m,self.uid,'leave',self.now);self.assertNotIn('finale',m)

    def test_leaving_during_finale_preserves_confirmed_winner(self):
        self.start();self.hit();m=self.act(self.a,'leave').json['match']
        self.assertEqual(m['status'],'finished');self.assertEqual(m['winner'],self.uid)
        self.assertEqual(m['result'],'best_of_three')
        self.assertEqual(self.a.get('/social/boxing/belts/'+str(self.pa)).json['belts'],1)
