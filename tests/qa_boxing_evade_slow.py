"""Local real-key lean dodge: only attacker slows, expiry or counter clears it."""
import os,time
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];assert root.startswith('http://127.0.0.1:')
def account(c):
 assert c.request.post(root+'/auth/register',data={'email':f'evade{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']};pid=c.request.post(root+'/profiles',headers=h,data={'name':'Evade '+str(time.time_ns())[-7:]}).json()['profile']['id'];assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{}}).ok
 return c.request.get(root+'/social/me',headers=h).json()['account_id'],pid,h
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 a=b.new_context();g=b.new_context();uid,pid,h=account(a);gid,gpid,gh=account(g);a.request.post(root+'/social/friends',headers=h,data={'action':'request','account_id':gid});g.request.post(root+'/social/friends',headers=gh,data={'action':'accept','account_id':uid})
 m=a.request.post(root+'/social/boxing/invite',headers=h,data={'profile':pid,'friend':gid,'control_mode':'computer'}).json();mid=m['id'];g.request.post(root+'/social/boxing/'+mid,headers=gh,data={'action':'accept','profile':gpid});g.request.post(root+'/social/boxing/'+mid,headers=gh,data={'action':'ready'})
 p=a.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(root+'/45-fitness-coach?lang=en');p.locator('#homeBoxingTile').click();p.wait_for_function("!document.querySelector('[data-mode=friends]').disabled");p.locator('[data-mode=friends]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-primary').click();p.get_by_role('button',name='Return to match',exact=True).click();p.wait_for_function("Boxing.state.status==='active'",timeout=15000);p.wait_for_function('Boxing.world.actors.every(a=>a.body)',timeout=60000)
 p.locator('.cage-canvas').click();p.keyboard.down('x');p.wait_for_function('Boxing.state.players[0].slip<-.35')
 def attack(seq):
  r=g.request.post(root+'/social/boxing/'+mid,headers=gh,data={'action':'left','seq':seq,'input_source':'keyboard','strike_id':'evade-'+str(seq)});assert r.ok,r.text()
 attack(1);p.wait_for_function("Boxing.state.event?.result==='dodge'&&Boxing.state.players[1].evade_slow_until>0",timeout=5000);assert p.evaluate('Boxing.state.players[0].hp')==50
 p.evaluate('window.clocks=Boxing.world.actors.map(a=>a.now());window.probeTime=performance.now()');p.wait_for_timeout(600);rates=p.evaluate('Boxing.world.actors.map((a,i)=>(a.now()-clocks[i])/(performance.now()-probeTime))');assert .9<rates[0]<1.1 and .35<rates[1]<.45,rates
 deadline=p.evaluate('Boxing.state.players[1].evade_slow_until');p.wait_for_function('Boxing.world.actors[1].motionClock.speed===1',timeout=6500);assert p.evaluate('Date.now()/1000')>=deadline-.2
 attack(2);p.wait_for_function('v=>Boxing.state.players[1].evade_slow_until>v',arg=deadline,timeout=4000);p.keyboard.press('q');p.wait_for_function('Boxing.state.players[1].evade_slow_until===0&&Boxing.world.actors[1].motionClock.speed===1',timeout=2500)
 assert p.evaluate('Boxing.state.pending_strikes?.some(s=>s.counter)||Boxing.state.events.some(e=>e.counter)');p.keyboard.up('x');p.locator('.boxing-back').click();assert not errors,errors
 print('PASS actual lean dodge, zero damage, only attacker animation at 40%, five-second expiry without counter, immediate cancellation and counter strike on Q')
 b.close()
