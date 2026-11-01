"""Deciding strikes, both viewpoints, bot ceremonies and friend-only belt collection."""
import os,time,json,sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];dbpath=os.environ['BOXING_TEST_DB'];assert root.startswith('http://127.0.0.1:') and dbpath.startswith('/tmp/')
out=Path('work/boxing-finale-review');out.mkdir(parents=True,exist_ok=True)
def account(c,name):
 assert c.request.post(root+'/auth/register',data={'email':f'finale{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']};pid=c.request.post(root+'/profiles',headers=h,data={'name':name+' '+str(time.time_ns())[-5:]}).json()['profile']['id'];assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{}}).ok
 return c.request.get(root+'/social/me',headers=h).json()['account_id'],pid,h
def menu(p,mode):
 p.locator('#homeBoxingTile').click();p.wait_for_function(f"!document.querySelector('[data-mode={mode}]').disabled");p.locator(f'[data-mode={mode}]').click();p.locator('[data-control=computer]').click()
def active(p):
 p.wait_for_function("Boxing.state?.status==='active'",timeout=25000);p.wait_for_function('Boxing.world?.actors.every(a=>a.body)',timeout=60000)
def final(p):
 p.wait_for_function("Boxing.world?.finale?.active&&Boxing.world.finale.age>1.85&&Boxing.world.finale.age<3.5",timeout=7000)
 assert p.locator('.boxing-cinematic-title').is_visible();assert p.locator('.boxing-result').is_hidden()
 assert p.evaluate('Boxing.world.actors.every(a=>a.neck.parent&&a.body&&a.root.visible)')
 assert p.evaluate('!Boxing.world.actors.some(a=>a.belt?.visible)')
def ceremony(p,winner):
 p.wait_for_function("Boxing.state?.status==='finished'&&Boxing.world.actors.some(a=>a.belt?.visible)",timeout=15000)
 assert p.evaluate('Boxing.state.winner')==winner
 assert not p.evaluate('Boxing.world.finale.active||!!Boxing.world.finale.effect')
 assert p.locator('.boxing-result').is_visible();assert p.locator('.boxing-result img').is_visible()
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-background-timer-throttling','--disable-renderer-backgrounding'])
 a=b.new_context(viewport={'width':1200,'height':950});g=b.new_context(viewport={'width':390,'height':900});uid,pid,h=account(a,'Blue');gid,gpid,gh=account(g,'Gold')
 a.request.post(root+'/social/friends',headers=h,data={'action':'request','account_id':gid});g.request.post(root+'/social/friends',headers=gh,data={'action':'accept','account_id':uid})
 with sqlite3.connect(dbpath) as db:db.execute("INSERT INTO account_roles(account_id,role) VALUES(?,'admin')",(uid,))
 m=a.request.post(root+'/social/boxing/invite',headers=h,data={'profile':pid,'friend':gid,'control_mode':'computer','custom_settings':{'hp':2,'armor':10,'level':3}}).json();mid=m['id'];assert g.request.post(root+'/social/boxing/'+mid,headers=gh,data={'action':'accept','profile':gpid}).ok
 host=a.new_page();guest=g.new_page();errors=[]
 for p in [host,guest]:
  p.on('pageerror',lambda e:errors.append(str(e)));p.goto(root+'/45-fitness-coach?lang=en');menu(p,'friends');p.locator('.fighter-primary').click();p.get_by_role('button',name='Return to match',exact=True).click()
 for p in [host,guest]:active(p)
 host.emulate_media(reduced_motion='reduce');guest.bring_to_front();guest.locator('.cage-canvas').click();guest.keyboard.press('q')
 guest.wait_for_function("Boxing.state.status==='round_break'",timeout=6000);assert guest.evaluate('!Boxing.state.finale&&!Boxing.world.finale.active')
 guest.wait_for_function("Boxing.state.status==='active'&&Boxing.state.round===2",timeout=15000);guest.keyboard.press('e');final(guest)
 assert guest.evaluate('!!Boxing.world.finale.effect&&Boxing.world.finale.drops.geometry.attributes.position.count===36')
 guest.locator('.boxing-arena').screenshot(path=str(out/'mobile-final-blow.png'));assert guest.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
 assert host.evaluate('Boxing.world.finale.active&&Boxing.world.finale.reduced&&!Boxing.world.finale.effect')
 guest.keyboard.press('q');guest.wait_for_timeout(400);assert guest.evaluate('Boxing.state.players[0].hp===0&&Boxing.state.players[1].wins===2')
 for p in [host,guest]:ceremony(p,gid)
 assert g.request.get(root+f'/social/boxing/belts/{gpid}',headers=gh).json()['belts']==1
 guest.locator('.boxing-arena').screenshot(path=str(out/'friend-belt.png'))
 print('PASS decisive friend strike only, two viewpoints, mobile framing, reduced-motion fallback, no bonus attack, then winner belt',flush=True)
 host.locator('.boxing-back').click();guest.locator('.boxing-back').click()
 # Disposable local fixtures shorten two bot matches without changing application logic.
 for difficulty,bot_wins in [('easy',False),('hard',True)]:
  host.emulate_media(reduced_motion='no-preference');host.locator('[data-mode=bot]').click();host.locator(f'[data-difficulty={difficulty}]').click();host.locator('[data-control=computer]').click();host.locator('.fighter-primary').click();active(host)
  bid=host.evaluate('Boxing.state.id')
  with sqlite3.connect(dbpath) as db:
   m=json.loads(db.execute('SELECT state FROM boxing_matches WHERE id=?',(bid,)).fetchone()[0]);m['round']=2
   for i,p in enumerate(m['players']):p.update(x=-.48 if i==0 else .48,z=0,move=0,side=0,slip=0,bend=0,crouch=0,guard_until=0)
   wi=1 if bot_wins else 0;m['players'][wi]['wins']=1;m['players'][1-wi]['hp']=1
   if not bot_wins:m['brain'].update(next_tick=time.time()+100,next_attack=time.time()+100)
   else:m['brain'].update(next_tick=0,next_attack=0,next_choice=0)
   db.execute('UPDATE boxing_matches SET state=? WHERE id=?',(json.dumps(m),bid))
  host.wait_for_function('Boxing.state.players.some(p=>p.hp===1)',timeout=5000)
  if not bot_wins:host.locator('.cage-canvas').click();host.keyboard.press('q')
  final(host);host.locator('.boxing-arena').screenshot(path=str(out/f'{difficulty}-final-blow.png'))
  ceremony(host,m['players'][wi]['uid']);assert 'Bot matches do not add profile belts' in host.locator('.boxing-result').inner_text()
  assert a.request.get(root+f'/social/boxing/belts/{pid}',headers=h).json()['belts']==0
  host.locator('.boxing-arena').screenshot(path=str(out/f'{difficulty}-belt.png'));host.locator('.boxing-back').click()
  assert host.evaluate('Boxing.world===null');print('PASS',difficulty,'bot finale/ceremony, correct winner, no profile belt and scene cleanup',flush=True)
 assert not errors,errors;b.close()
