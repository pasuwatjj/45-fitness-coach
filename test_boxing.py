import copy,unittest
from unittest.mock import patch
import boxing
import test_v13 as fixtures
import app as server
class BoxingTests(unittest.TestCase):
    def setUp(self):
        fixtures.RouteTests.setUp(self)
        self.uid=int(self.owner.split(':')[1]);self.other=int(self.reg.items[self.tb]['owner'].split(':')[1]);self.now=1000
        self.patcher=patch('boxing.clock',side_effect=lambda:self.now);self.patcher.start();self.addCleanup(self.patcher.stop)
        self.a.post('/social/friends',json={'action':'request','account_id':self.other});self.b.post('/social/friends',json={'action':'accept','account_id':self.uid})
        def fighter(store,uid,pid):
            return dict(uid=uid,name='Test',model={},damage={'left':2,'right':4},hp=10,armor=10,ready=False,seen=self.now,seq=0,last_punch=0,last_dodge=0,guard_until=0,dodge_until=0,pose='idle')
        self.fp=patch('boxing.fighter',side_effect=fighter);self.fp.start();self.addCleanup(self.fp.stop)
    def create(self):
        r=self.a.post('/social/boxing/invite',json={'friend':self.other,'profile':1});self.assertEqual(r.status_code,200,r.json);self.mid=r.json['id'];return r.json
    def act(self,client,action,seq=1):return client.post('/social/boxing/'+self.mid,json={'action':action,'seq':seq,'profile':1})
    def start(self):
        self.create();self.assertEqual(self.act(self.b,'accept').status_code,200);self.act(self.a,'ready');r=self.act(self.b,'ready');self.assertEqual(r.json['match']['start'],1005);self.now+=5
    def test_private_invitation_and_chat(self):
        self.create();self.assertEqual(server.app.test_client().get('/social/boxing/'+self.mid).status_code,401)
        self.assertEqual(self.act(self.a,'accept').status_code,409)
        msgs=self.b.get('/social/chat/'+str(self.uid)).json['messages'];self.assertIn('#boxing:'+self.mid,msgs[-1]['body'])
        self.assertEqual(self.act(self.b,'decline').json['match']['status'],'declined')
    def test_ready_countdown_and_damage(self):
        self.start();self.now-=1;self.assertEqual(self.act(self.a,'right').status_code,400);self.now+=1
        m=self.act(self.a,'right').json['match'];self.assertEqual(m['players'][1]['hp'],6)
        self.now+=1;m=self.act(self.a,'right').json['match'];self.assertEqual(m['players'][1]['hp'],6) # duplicate
        m=self.act(self.a,'right',2).json['match'];self.assertEqual(m['players'][1]['hp'],2)
        self.now+=1;m=self.act(self.a,'left',3).json['match'];self.assertEqual(m['status'],'finished');self.assertEqual(m['winner'],self.uid)
    def test_guard_break_and_dodge(self):
        self.start()
        for i in range(10):
            self.now+=1;self.act(self.b,'guard',i+1);m=self.act(self.a,'left',i+1).json['match'];self.assertEqual(m['players'][1]['hp'],10)
        self.assertEqual(m['players'][1]['armor'],0);self.now+=1;self.act(self.b,'guard',11);m=self.act(self.a,'right',11).json['match'];self.assertEqual(m['players'][1]['hp'],6)
    def test_dodge_cost_window_and_punch_rate(self):
        self.start();self.act(self.b,'dodge');m=self.act(self.a,'right').json['match'];self.assertEqual(m['players'][1]['hp'],10);self.assertEqual(m['players'][1]['armor'],9)
        self.act(self.b,'dodge',2);self.now+=.5;m=self.act(self.a,'right',2).json['match'];self.assertEqual(m['players'][1]['hp'],6)
        m=self.act(self.a,'right',3).json['match'];self.assertEqual(m['players'][1]['hp'],6)
    def test_disconnect_expiry_and_invalid(self):
        self.create();self.assertEqual(self.a.post('/social/boxing/invite',json=[]).status_code,400);self.now+=121
        self.assertEqual(self.a.get('/social/boxing/'+self.mid).json['match']['status'],'expired')
    def test_leave_awards_opponent(self):
        self.start();m=self.act(self.b,'leave').json['match'];self.assertEqual(m['winner'],self.uid)
    def test_real_avatar_and_profile_ownership(self):
        self.fp.stop()
        self.assertEqual(self.a.post('/social/boxing/invite',json={'friend':self.other,'profile':self.pb}).status_code,400)
        self.assertEqual(self.a.post('/social/boxing/invite',json={'friend':self.other,'profile':self.pa}).status_code,400)
        self.assertEqual(self.a.post(f'/profiles/{self.pa}/character',json={'appearance':{'hair_color':'#112233'}}).status_code,200)
        r=self.a.post('/social/boxing/invite',json={'friend':self.other,'profile':self.pa});self.assertEqual(r.status_code,200,r.json);self.assertEqual(r.json['players'][0]['model']['appearance']['hair_color'],'#112233');self.assertEqual(r.json['players'][0]['damage'],{'left':1,'right':1})
        self.assertNotIn('dimensions',r.json['players'][0]['model'])
    def test_rematch_after_finished_room_heartbeat(self):
        self.start();self.act(self.b,'leave');self.now+=1;self.act(self.a,'heartbeat');self.create()
