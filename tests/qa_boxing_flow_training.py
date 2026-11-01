"""Local-only HP upgrades, auto lifecycle and combat animation under delayed replies."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os,time
root=os.environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5073');assert root.startswith('http://127.0.0.1:')
out=Path('work/boxing-flow-review');out.mkdir(parents=True,exist_ok=True)
def account(c,name):
 assert c.request.post(root+'/auth/register',data={'email':f'flow{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']};pid=c.request.post(root+'/profiles',headers=h,data={'name':name+' '+str(time.time_ns())[-5:]}).json()['profile']['id'];assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{}}).ok
 return c.request.get(root+'/social/me',headers=h).json()['account_id'],pid,h
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 c=b.new_context(viewport={'width':1280,'height':950});d=b.new_context();uid,pid,h=account(c,'Flow');other,opid,oh=account(d,'Friend');p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 p.goto(root+'/45-fitness-coach?lang=en');p.locator('#homeBoxingTile').click();p.wait_for_function("!document.querySelector('[data-mode=practice]').disabled")
 p.locator('[data-mode=practice]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-primary').click();p.wait_for_function("document.querySelector('.boxing-training button')?.disabled===false&&Boxing.world?.actors[0]?.body",timeout=60000)
 auto=p.locator('.boxing-training button').first;auto.click();p.wait_for_function("document.querySelector('.boxing-training strong').textContent==='MAX HP 12'",timeout=15000)
 assert '20 punches' in p.locator('.boxing-training span').inner_text();assert p.locator('.hp-bar progress').evaluate('(e)=>e.max')==12
 p.wait_for_function("document.querySelector('.boxing-training strong').textContent==='MAX HP 14'",timeout=22000);auto.click();assert auto.get_attribute('aria-pressed')=='false'
 assert '40 punches' in p.locator('.boxing-training span').inner_text();p.locator('.boxing-training').screenshot(path=str(out/'hp-14.png'))
 p.locator('.boxing-back').click();p.wait_for_function("Boxing.mode==='menu'");data=c.request.get(root+f'/social/boxing/training/{pid}',headers=h).json();assert data['max_hp']==14 and data['total_hits']>=30
 p.reload();p.locator('#homeBoxingTile').click();p.wait_for_function("document.querySelector('.fighter-hp-level')?.textContent.includes('MAX HP 14')");assert c.request.get(root+f'/social/boxing/training/{pid}',headers=h).json()['total_hits']==data['total_hits']
 p.locator('[data-mode=bot]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-primary').click();p.wait_for_function("Boxing.state?.status==='active'",timeout=15000);p.wait_for_function('Boxing.world.actors.every(a=>a.body)',timeout=60000)
 assert p.evaluate('Boxing.state.players[0].max_hp===14&&Boxing.state.players[1].max_hp===20');assert p.locator('.boxing-training').is_hidden()
 # Delayed replies must not delay local wind-up or crouch. Stable HUD nodes avoid layout churn.
 p.evaluate("""window.flowFetch=window.fetch;window.fetch=async(...args)=>{const r=await window.flowFetch(...args);if(String(args[0]).includes('/social/boxing/'))await new Promise(resolve=>setTimeout(resolve,400));return r};window.hudChanges=0;new MutationObserver(()=>hudChanges++).observe(document.querySelector('.boxing-hud'),{childList:true});window.remoteAges=[];const punch=Boxing.world.actors[1].punch.bind(Boxing.world.actors[1]);Boxing.world.actors[1].punch=(hand,token,kind,age)=>{remoteAges.push(age);punch(hand,token,kind,age)};void 0""")
 p.locator('.cage-canvas').focus();p.evaluate('window.inputAt=performance.now()');p.keyboard.press('q');p.wait_for_function('Boxing.world.actors[0].punchAt>inputAt',timeout=1000);assert p.evaluate('Boxing.world.actors[0].punchAt-inputAt')<150
 p.keyboard.down('c');p.wait_for_function('Boxing.world.states[0].crouch>.5',timeout=500);p.keyboard.up('c');p.wait_for_function('Boxing.world.states[0].crouch===0',timeout=500)
 p.wait_for_function('remoteAges.length>0',timeout=5000);assert p.evaluate('remoteAges.every(n=>n<=45)');assert p.evaluate('hudChanges')<15
 p.evaluate('window.fetch=window.flowFetch;void 0');p.locator('.boxing-arena').screenshot(path=str(out/'flow-match.png'));p.locator('.boxing-back').click();p.wait_for_function("Boxing.mode==='menu'")
 # Friend HP is profile-owned; the untrained friend remains at ten.
 c.request.post(root+'/social/friends',headers=h,data={'action':'request','account_id':other});d.request.post(root+'/social/friends',headers=oh,data={'action':'accept','account_id':uid})
 r=c.request.post(root+'/social/boxing/invite',headers=h,data={'profile':pid,'friend':other,'control_mode':'computer'});assert r.ok,r.text();mid=r.json()['id'];d.request.post(root+'/social/boxing/'+mid,headers=oh,data={'action':'accept','profile':opid});d.request.post(root+'/social/boxing/'+mid,headers=oh,data={'action':'ready'})
 p.locator('[data-mode=friends]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-primary').click();p.get_by_role('button',name='Return to match',exact=True).click();p.wait_for_function("Boxing.state?.status==='active'",timeout=15000)
 assert p.evaluate('Boxing.state.players[0].max_hp===14&&Boxing.state.players[1].max_hp===10');p.locator('.boxing-back').click();p.wait_for_function("Boxing.mode==='menu'")
 # Auto is explicitly stopped when navigating away, and never restarts by itself.
 p.set_viewport_size({'width':390,'height':900});p.locator('[data-mode=practice]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-primary').click();p.wait_for_function("!document.querySelector('.boxing-training button').disabled");p.locator('.boxing-training button').first.click();p.wait_for_timeout(800);p.evaluate("setTab('home')");p.wait_for_timeout(1200);stopped=c.request.get(root+f'/social/boxing/training/{pid}',headers=h).json()['total_hits'];p.wait_for_timeout(1000);assert c.request.get(root+f'/social/boxing/training/{pid}',headers=h).json()['total_hits']==stopped
 p.evaluate("setTab('boxing')");p.wait_for_function("Boxing.mode==='practice'&&!document.querySelector('.boxing-training button').disabled");assert p.locator('.boxing-training button').first.get_attribute('aria-pressed')=='false';assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1');p.locator('.boxing-training').screenshot(path=str(out/'hp-mobile.png'))
 p.locator('.boxing-back').click();p.wait_for_function("Boxing.mode==='menu'");p.locator('[data-mode=bot]').click();p.locator('[data-difficulty=hard]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-primary').click();p.wait_for_function("Boxing.state?.status==='countdown'",timeout=15000);assert p.evaluate('Boxing.state.players[1].hp===50&&Boxing.state.players[1].max_hp===50');p.locator('.boxing-back').click()
 assert not errors,errors
 print('PASS 10/20 incremental bag goals, HP 12/14 and reload persistence, visible auto toggle/stop/resume lifecycle, mobile panel, own HP in friend/bot matches, fixed 20/50 bot HP, local animation during 400ms replies and full remote wind-up')
 b.close()
