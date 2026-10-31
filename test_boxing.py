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
            return dict(profile_id=pid,uid=uid,name='Test',model={},damage={'left':2,'right':4},hp=10,armor=10,ready=False,seen=self.now,seq=0,last_punch=0,last_dodge=0,guard_until=0,dodge_until=0,pose='idle')
        self.fp=patch('boxing.fighter',side_effect=fighter);self.fp.start();self.addCleanup(self.fp.stop)
    def create(self):
        r=self.a.post('/social/boxing/invite',json={'friend':self.other,'profile':1});self.assertEqual(r.status_code,200,r.json);self.mid=r.json['id'];return r.json
    def act(self,client,action,seq=1,**controls):return client.post('/social/boxing/'+self.mid,json={'action':action,'seq':seq,'profile':1,**controls})
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
    def test_guard_hold_break_and_trophy_once(self):
        self.start();n=0
        for i in range(7):
            n+=1;self.act(self.b,'control',n,guard=True)
            if i<6:self.now+=.5
        for i in range(10):
            n+=1;self.act(self.b,'control',n,guard=True);m=self.act(self.a,'left',i+1).json['match'];self.assertEqual(m['players'][1]['hp'],10);self.now+=.5
        self.assertEqual(m['players'][1]['armor'],0)
        for i in range(3):
            n+=1;self.act(self.b,'control',n,guard=True);m=self.act(self.a,'right',11+i).json['match'];self.now+=.5
        self.assertEqual(m['winner'],self.uid);self.assertTrue(m['trophy_awarded'])
        for _ in range(3):self.a.get('/social/boxing/'+self.mid);self.act(self.a,'heartbeat')
        self.assertEqual(self.a.get('/social/boxing/trophies/'+str(self.pa)).json['trophies'],1)
        self.assertEqual(self.b.get('/social/boxing/trophies/'+str(self.pa)).status_code,404)
    def test_before_three_seconds_hits_hp_and_lowering_resets(self):
        self.start()
        for i in range(5):self.act(self.b,'control',i+1,guard=True);self.now+=.5
        m=self.act(self.a,'right').json['match'];self.assertEqual(m['players'][1]['hp'],6);self.assertEqual(m['players'][1]['armor'],10)
        self.act(self.b,'control',6,guard=False);self.now+=.5;m=self.act(self.b,'control',7,guard=True).json['match'];self.assertEqual(m['players'][1]['guard_until'],0)
    def test_walk_no_armor_cost_and_range(self):
        self.start()
        for i in range(12):
            self.act(self.b,'control',i+1,move=-1);self.now+=.25;self.act(self.a,'heartbeat')
        m=self.act(self.a,'right').json['match'];self.assertEqual(m['event']['result'],'miss');self.assertEqual(m['players'][1]['hp'],10);self.assertEqual(m['players'][1]['armor'],10)
        pos=m['players'][1]['position'];self.now+=3;m=self.act(self.a,'heartbeat').json['match'];self.assertLessEqual(m['players'][1]['position']-pos,.1)
    def test_invalid_vectors_and_legacy_dodge(self):
        self.start();self.assertEqual(self.act(self.a,'dodge').status_code,400)
        self.assertEqual(self.act(self.a,'control',arms={'left':{'upper':[99,0,0],'lower':[0,0,0]},'right':{'upper':[0,0,0],'lower':[0,0,0]}}).status_code,400)
        self.assertEqual(self.act(self.a,'control',move=2).status_code,400)
    def test_cancelled_countdown_no_trophy(self):
        self.create();self.act(self.b,'accept');self.act(self.a,'ready');self.act(self.b,'ready');self.act(self.b,'leave')
        self.assertEqual(self.a.get('/social/boxing/trophies/'+str(self.pa)).json['trophies'],0)
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
