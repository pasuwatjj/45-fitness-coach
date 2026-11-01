"""Admin-only match overrides, immutable rules, no progression or belt writes."""
import copy,unittest
from unittest.mock import patch
import boxing,boxing_cage,community
import test_boxing as legacy

class AdminRooms(unittest.TestCase):
    def setUp(self):
        legacy.BoxingTests.setUp(self)
        community.schema(self.store);boxing.schema(self.store)
    def grant(self):
        with self.store.connect() as db:db.execute("INSERT INTO account_roles(account_id,role) VALUES(?,'admin')",(self.uid,))
    def invite(self,settings=None):
        data=dict(friend=self.other,profile=self.pa,control_mode='computer')
        if settings is not None:data['custom_settings']=settings
        return self.a.post('/social/boxing/invite',json=data)
    def test_server_permission_and_revocation(self):
        config=dict(hp=200,armor=30,level=8)
        self.assertFalse(self.a.get('/social/boxing/capabilities').json['custom_rooms'])
        self.assertEqual(self.invite(config).status_code,403)
        self.grant();self.assertTrue(self.a.get('/social/boxing/capabilities').json['custom_rooms'])
        with self.store.connect() as db:db.execute('DELETE FROM account_roles WHERE account_id=?',(self.uid,))
        self.assertEqual(self.invite(config).status_code,403)
        self.assertEqual(self.invite().status_code,200) # Normal friend invitations remain available.
    def test_strict_ranges(self):
        self.grant()
        for config in [{},[],{'hp':50,'armor':10},dict(hp=True,armor=10,level=1),dict(hp=0,armor=10,level=1),dict(hp=10001,armor=10,level=1),dict(hp=50,armor=-1,level=1),dict(hp=50,armor=1001,level=1),dict(hp=50,armor=10,level=101),dict(hp=50,armor=10,level=1.5)]:
            self.assertEqual(self.invite(config).status_code,400,config)
    def test_both_fighters_round_reset_regeneration_and_winner_belt(self):
        self.grant();r=self.invite(dict(hp=200,armor=30,level=8));self.assertEqual(r.status_code,200,r.json);mid=r.json['id']
        m=self.b.post('/social/boxing/'+mid,json={'action':'accept','profile':self.pb}).json['match']
        for p in m['players']:
            self.assertEqual((p['hp'],p['max_hp'],p['armor'],p['max_armor'],p['kick_damage']),(200,200,30,30,8))
            self.assertEqual(p['damage'],dict(left=8,right=8));self.assertTrue(all(v['level']==8 for v in p['model']['growth']['parts'].values()))
        self.assertEqual(self.a.post('/social/boxing/'+mid,json={'action':'heartbeat','custom_settings':dict(hp=1,armor=0,level=1)}).status_code,400)
        m.update(rules=8,status='active',round_start=self.now,start=self.now)
        for p in m['players']:p.update(armor=29,armor_regen_at=self.now)
        boxing_cage.regenerate(m,self.now+10);self.assertEqual([p['armor'] for p in m['players']],[30,30])
        boxing.knockout(m,m['players'][0],self.now);boxing.advance(m,self.now+10)
        self.assertEqual([p['hp'] for p in m['players']],[200,200]);self.assertEqual([p['armor'] for p in m['players']],[30,30])
        boxing.finish(m,self.uid,'knockout',self.now+11)
        with self.store.connect() as db:
            boxing.award(db,m,self.now+11);self.assertEqual(db.execute('SELECT COUNT(*) FROM boxing_trophies').fetchone()[0],1)
    def test_zero_armor_and_saved_growth_untouched(self):
        self.grant();self.fp.stop();self.a.post('/profiles/'+str(self.pa)+'/character',json={'appearance':{}})
        before=boxing.fighter(self.store,self.uid,self.pa)
        m=self.invite(dict(hp=100,armor=0,level=12)).json
        self.assertEqual(m['players'][0]['max_armor'],0)
        after=boxing.fighter(self.store,self.uid,self.pa)
        self.assertEqual(before['model'],after['model']);self.assertEqual(after['hp'],50);self.assertEqual(after['damage'],dict(left=1,right=1))

if __name__=='__main__':unittest.main()
