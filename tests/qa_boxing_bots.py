"""Disposable local accounts only: complete Bot UI and server-driven rounds."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os,time
root=os.environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5070')
assert root.startswith('http://127.0.0.1:')
out=Path('work/boxing-bots-review');out.mkdir(parents=True,exist_ok=True)
def account(c):
 assert c.request.post(root+'/auth/register',data={'email':f'bot{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']}
 pid=c.request.post(root+'/profiles',headers=h,data={'name':'Bot QA '+str(time.time_ns())[-5:]}).json()['profile']['id']
 assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{'gender':'female','top_color':'#7733aa'}}).ok
 return pid,h
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 c=b.new_context(viewport={'width':1280,'height':900});pid,h=account(c);p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 p.goto(root+'/45-fitness-coach?lang=en');p.locator('#homeBoxingTile').click();p.wait_for_function("!document.querySelector('[data-mode=bot]').disabled")
 p.locator('[data-mode=bot]').click();assert p.locator('[data-difficulty=easy]').get_attribute('aria-checked')=='true';assert p.locator('.fighter-primary').is_disabled()
 p.locator('[data-control=computer]').click();p.locator('.fighter-dialog').screenshot(path=str(out/'bot-select.png'));p.locator('.fighter-primary').click()
 p.wait_for_function("Boxing.state?.kind==='bot'&&Boxing.state.status==='active'",timeout=15000)
 p.wait_for_function("Boxing.world?.actors.length===2&&Boxing.world.actors.every(a=>a.body)",timeout=60000)
 assert p.evaluate("JSON.stringify(Boxing.state.players[0].damage)===JSON.stringify(Boxing.state.players[1].damage)&&JSON.stringify(Boxing.state.players[0].model.growth)===JSON.stringify(Boxing.state.players[1].model.growth)")
 assert p.evaluate("Boxing.world.states[1].controlMode==='computer'&&!Boxing.world.bag.visible&&Boxing.state.difficulty==='easy'&&Boxing.state.players[1].max_hp===20")
 # Both attack and knockback are authoritative, using actual keyboard play.
 p.evaluate("const draw=Boxing.world.renderer.render.bind(Boxing.world.renderer);let last=0;Boxing.world.renderer.render=(...args)=>{if(performance.now()-last>80){last=performance.now();draw(...args)}};window.hitEvidence=[];setInterval(()=>{for(const e of Boxing.state?.events||[])if(e.knockback&&!hitEvidence.some(v=>v.id===e.id))hitEvidence.push(e)},80);void 0")
 mid=p.evaluate('Boxing.state.id');p.evaluate("setTab('home')");p.wait_for_timeout(500);p.evaluate("setTab('boxing')");p.wait_for_function("Boxing.world.running&&Boxing.mode==='bot'&&Boxing.state.status==='active'");assert p.evaluate('Boxing.state.id')==mid
 deadline=time.time()+65
 while time.time()<deadline and p.evaluate("Boxing.state.status!=='finished'"):
  state=p.evaluate('({status:Boxing.state.status,players:Boxing.state.players})')
  if state['status']=='active':
   a,q=state['players'];distance=((a.get('x',-.7)-q.get('x',.7))**2+(a.get('z',0)-q.get('z',0))**2)**.5
   if distance>1.15:p.keyboard.down('w')
   else:p.keyboard.up('w')
   p.keyboard.press('q' if int(time.time()*2)%2 else 'e')
  else:p.keyboard.up('w')
  p.wait_for_timeout(450)
 p.keyboard.up('w');p.wait_for_function("Boxing.state.status==='finished'",timeout=12000)
 assert p.evaluate('hitEvidence.length>3');assert p.evaluate('Boxing.state.round>=2&&Boxing.state.rounds.length>=2');assert not p.evaluate('!!Boxing.state.belt_awarded')
 assert p.locator('.boxing-result').is_visible();assert p.locator('.boxing-rematch').is_visible();p.locator('.boxing-arena').screenshot(path=str(out/'bot-finished.png'))
 p.locator('.boxing-rematch').click();p.wait_for_function("id=>Boxing.state?.id!==id&&Boxing.state?.status==='countdown'",arg=mid,timeout=15000)
 p.locator('.boxing-back').click();p.wait_for_function("Boxing.mode==='menu'&&Boxing.world===null")
 p.set_viewport_size({'width':390,'height':900});p.locator('[data-mode=bot]').click();p.locator('[data-difficulty=hard]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-dialog').screenshot(path=str(out/'bot-mobile.png'));assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1');p.locator('.fighter-primary').click()
 p.wait_for_function("Boxing.state?.difficulty==='hard'&&Boxing.state.status==='active'",timeout=15000)
 p.wait_for_function('Boxing.state.players[1].last_punch>0',timeout=5000);p.wait_for_function("Boxing.world.actors.every(a=>a.body)")
 assert p.evaluate("Boxing.state.brain.plan.reaction===.14&&Boxing.state.players[0].hp<=10&&Boxing.state.players[1].armor===10&&Boxing.state.players[1].max_hp===50")
 p.locator('.boxing-arena').screenshot(path=str(out/'bot-hard.png'));p.locator('.boxing-back').click();p.wait_for_function("Boxing.mode==='menu'")
 assert not errors,errors
 print('PASS real easy bot match through all rounds/results, matched damage/growth and fixed 20/50 HP, bare-hand actors, authoritative hit knockback, navigation resume, rematch, hard bot attack, mobile difficulty selection; no browser errors')
 b.close()
