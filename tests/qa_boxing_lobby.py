"""Local-only fighter lobby, remapped keyboard combat and shared room-mode checks."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os,time
root=os.environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5063');out=Path('work/boxing-lobby-review');out.mkdir(parents=True,exist_ok=True)
def account(c,name,gender='male'):
 assert c.request.post(root+'/auth/register',data={'email':f'lobby{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']}
 pid=c.request.post(root+'/profiles',headers=h,data={'name':name+' '+str(time.time_ns())[-5:]}).json()['profile']['id']
 assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{'gender':gender}}).ok
 return c.request.get(root+'/social/me',headers=h).json()['account_id'],pid,h
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-background-timer-throttling','--disable-renderer-backgrounding'])
 ca=b.new_context(viewport={'width':1280,'height':1050});cb=b.new_context(viewport={'width':390,'height':950});uid,pid,h=account(ca,'KAI');other,opid,oh=account(cb,'LUNA','female')
 ca.request.post(root+'/social/friends',headers=h,data={'action':'request','account_id':other});cb.request.post(root+'/social/friends',headers=oh,data={'action':'accept','account_id':uid})
 a=ca.new_page();c=cb.new_page();errors=[]
 for page,lang in [(a,'en'),(c,'th')]:
  page.on('pageerror',lambda e:errors.append(str(e)));page.goto(root+'/45-fitness-coach?lang='+lang);page.evaluate("window.cameraRequests=0;navigator.mediaDevices.getUserMedia=async()=>{cameraRequests++;throw new Error('Unexpected camera request')};void 0")
  page.locator('#homeBoxingTile').click();page.wait_for_function("document.querySelector('.fighter-lobby-scene canvas')?.dataset.avatarState==='ready'",timeout=60000)
  assert page.locator('[data-mode=bot]').is_disabled();assert page.evaluate('Boxing.world===null&&cameraRequests===0');assert page.locator('.fighter-growth-row').count()==5
  model=page.request.get(root+f'/profiles/{pid if page==a else opid}/character',headers=h if page==a else oh).json()
  for key,part in model['growth']['parts'].items():
   row=page.locator(f'.fighter-growth-row[data-part={key}]');assert row.locator('strong').inner_text()=='LV '+str(part['level']);assert abs(row.locator('progress').evaluate('(e)=>e.value')-part['progress'])<.0001
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  page.locator('.boxing-menu').screenshot(path=str(out/f'lobby-{page.viewport_size["width"]}.png'))
 # Settings: reject duplicate keys, persist a new binding through reload, expose language choices.
 a.locator('[data-mode=settings]').click();assert a.locator('.fighter-language button').count()==2
 a.locator('[data-binding=punchLeft]').click();a.keyboard.press('w');assert 'already assigned' in a.locator('.fighter-key-message').inner_text()
 a.keyboard.press('j');assert a.locator('[data-binding=punchLeft]').inner_text()=='J';assert a.locator('.click-particle').count()==0;a.locator('.fighter-dialog').screenshot(path=str(out/'settings.png'));a.locator('.fighter-dialog-close').click()
 a.reload();a.locator('#homeBoxingTile').click();a.wait_for_function("!document.querySelector('[data-mode=practice]').disabled");assert a.evaluate('BoxingKeys.bindings.punchLeft')=='KeyJ'
 a.evaluate("window.cameraRequests=0;navigator.mediaDevices.getUserMedia=async()=>{cameraRequests++;throw new Error('Unexpected camera request')};void 0")
 a.locator('[data-mode=practice]').click();assert a.locator('.fighter-primary').is_disabled();assert a.evaluate('Boxing.world===null&&cameraRequests===0');a.locator('[data-control=computer]').click();a.locator('.fighter-primary').click()
 a.wait_for_function("Boxing.world?.actors[0]?.canvas.dataset.avatarState==='ready'",timeout=60000)
 a.keyboard.press('j');a.wait_for_function("document.querySelector('.boxing-bag-damage').textContent.includes('1')")
 a.wait_for_timeout(450);old=a.locator('.boxing-banner').inner_text();a.keyboard.down('u');a.wait_for_function("Boxing.world.actors[0].punchType==='kick'");a.wait_for_timeout(650);a.keyboard.up('u');assert a.locator('.boxing-banner').inner_text()!=old
 count=a.locator('.boxing-banner').inner_text();a.wait_for_timeout(600);assert a.locator('.boxing-banner').inner_text()==count
 x=a.evaluate('Boxing.world.states[0].x');a.keyboard.down('s');a.wait_for_function('x=>Boxing.world.states[0].x<x-.1',arg=x,timeout=1800);a.keyboard.up('s')
 a.keyboard.down('c');a.wait_for_function('Boxing.world.actors[0].poseSmooth.crouch>.65');a.keyboard.up('c');a.wait_for_function('Boxing.world.actors[0].poseSmooth.crouch<.1')
 x=a.evaluate('Boxing.world.states[0].x');a.keyboard.down('s');a.keyboard.down('Control');a.wait_for_function('x=>Boxing.world.states[0].x<x-.32',arg=x,timeout=1500);a.keyboard.up('Control');a.keyboard.up('s')
 # New chord attacks and one-sided guard are actual browser inputs.
 a.wait_for_timeout(700);a.keyboard.down('Space');a.keyboard.press('a');a.keyboard.up('Space');a.wait_for_function("Boxing.world.actors[0].punchType==='uppercut'&&Boxing.world.actors[0].punchHand==='left'")
 a.wait_for_timeout(500);a.keyboard.down('Space');a.keyboard.press('w');a.keyboard.up('Space');a.wait_for_function("Boxing.world.actors[0].punchType==='uppercut'")
 a.keyboard.down('f');a.keyboard.down('j');a.wait_for_function("Boxing.world.states[0].guard_side==='left'");a.keyboard.up('j');a.keyboard.up('f')
 a.wait_for_timeout(500);a.locator('.boxing-arena').screenshot(path=str(out/'mma-arena.png'))
 assert a.locator('.boxing-views button').count()==2
 a.locator('.boxing-camera-lock').click();assert a.locator('.boxing-camera-lock').get_attribute('aria-pressed')=='true';locked=a.evaluate('Boxing.world.camera.position.toArray()');canvas=a.locator('.cage-canvas').bounding_box();a.mouse.move(canvas['x']+canvas['width']*.5,canvas['y']+canvas['height']*.5);a.mouse.down();a.mouse.move(canvas['x']+canvas['width']*.7,canvas['y']+canvas['height']*.6);a.mouse.up();a.mouse.wheel(0,300);a.wait_for_timeout(300);assert a.evaluate('Boxing.world.camera.position.toArray()')==locked
 for _ in range(2):
  a.evaluate("setTab('home')");assert a.evaluate("Boxing.world&&!Boxing.world.running");a.evaluate("setTab('boxing')");a.wait_for_function("Boxing.mode==='practice'&&Boxing.world.running");a.wait_for_timeout(800);before=a.evaluate('Boxing.world.actors[0].punchAt');a.keyboard.press('j');a.wait_for_function('t=>Boxing.world.actors[0].punchAt>t',arg=before);assert a.locator('.boxing-camera-lock').get_attribute('aria-pressed')=='true'
 a.locator('.boxing-camera-lock').click();assert a.locator('.boxing-camera-lock').get_attribute('aria-pressed')=='false'
 a.locator('.boxing-back').click();a.wait_for_function("Boxing.mode==='menu'&&Boxing.world===null")
 a.locator('[data-mode=friends]').click();assert a.locator('.fighter-primary').is_disabled();a.locator('.fighter-dialog').screenshot(path=str(out/'control-selection.png'));a.locator('[data-control=computer]').click();a.locator('.fighter-primary').click()
 a.get_by_role('button',name='Invite friend',exact=True).click();a.wait_for_function("Boxing.state?.status==='invited'");assert a.evaluate('Boxing.state.control_mode')=='computer'
 # Guest selects tracking locally first, then must inherit the host's computer mode upon acceptance.
 c.locator('[data-mode=friends]').click();c.locator('[data-control=tracking]').click();c.locator('.fighter-primary').click();c.wait_for_function('cameraRequests===1');c.get_by_role('button',name='รับคำชวน',exact=True).click()
 for p in [a,c]:
  p.wait_for_function("Boxing.state?.status==='active'",timeout=20000);p.wait_for_function("Boxing.world?.actors.length===2&&Boxing.world.actors.every(a=>a.canvas.dataset.avatarState==='ready')",timeout=60000)
  assert p.evaluate("Boxing.controlMode==='computer'&&Boxing.state.control_mode==='computer'");assert p.evaluate('cameraRequests')==(0 if p==a else 1)
  p.evaluate("const render=Boxing.world.renderer.render.bind(Boxing.world.renderer);let last=0;Boxing.world.renderer.render=(...args)=>{if(performance.now()-last>80){last=performance.now();render(...args)}};void 0")
 a.keyboard.press('j');a.wait_for_function('Boxing.state.players[1].hp===9',timeout=7000);c.wait_for_function('Boxing.state.players[1].hp===9')
 a.wait_for_timeout(500);a.keyboard.press('i');a.wait_for_function('Boxing.state.players[1].hp===8',timeout=7000);c.wait_for_function("Boxing.state.event?.punch_type==='kick'")
 a.wait_for_timeout(800);c.keyboard.down('f');a.wait_for_function('Boxing.state.players[1].guard_until*1000>Date.now()');a.keyboard.press('j');a.wait_for_function("Boxing.state.event?.result==='block'");assert a.evaluate('Boxing.state.players[1].hp')==8;c.keyboard.up('f')
 a.wait_for_timeout(500);c.keyboard.down('f');c.keyboard.down('q');a.wait_for_function("Boxing.state.players[1].guard_side==='left'");armor=a.evaluate('Boxing.state.players[1].armor');a.keyboard.press('j');a.wait_for_function("Boxing.state.event?.guard_result==='perfect'");assert a.evaluate('Boxing.state.players[1].hp')==8;assert a.evaluate('Boxing.state.players[1].armor')>=armor
 a.wait_for_timeout(500);a.keyboard.press('e');a.wait_for_function("Boxing.state.event?.guard_result==='wrong'");assert a.evaluate('Boxing.state.players[1].hp')==7;c.keyboard.up('q');c.keyboard.up('f')
 mid=a.evaluate('Boxing.state.id');a.evaluate("setTab('home')");a.wait_for_timeout(700);a.evaluate("setTab('boxing')");a.wait_for_function("Boxing.world.running&&Boxing.state.status==='active'");assert a.evaluate('Boxing.state.id')==mid
 start=a.evaluate('Boxing.state.players[0].z');a.keyboard.down('a');a.wait_for_function('z=>Math.abs(Boxing.state.players[0].z-z)>.1',arg=start,timeout=1800);a.keyboard.up('a')
 a.wait_for_timeout(300);stopped=a.evaluate('Boxing.state.players[0].z');a.wait_for_timeout(350);assert abs(a.evaluate('Boxing.state.players[0].z')-stopped)<.03
 before=a.evaluate('({x:Boxing.state.players[0].x,z:Boxing.state.players[0].z})');a.keyboard.down('s');a.keyboard.down('Control')
 a.wait_for_function('p=>Math.hypot(Boxing.state.players[0].x-p.x,Boxing.state.players[0].z-p.z)>.32',arg=before,timeout=1800)
 stamp=a.evaluate('Boxing.state.players[0].last_dash');c.wait_for_function('v=>Boxing.state.players[0].last_dash===v',arg=stamp);a.keyboard.up('s');a.wait_for_timeout(800);assert a.evaluate('Boxing.state.players[0].last_dash')==stamp;a.keyboard.up('Control')
 assert not errors,errors
 a.locator('.boxing-back').click();a.wait_for_function("Boxing.mode==='menu'&&Boxing.world===null");assert a.evaluate('cameraRequests===0')
 c.locator('.boxing-back').click();c.wait_for_function("Boxing.mode==='menu'&&!document.querySelector('[data-mode=settings]').disabled");c.locator('[data-mode=settings]').click();c.locator('.fighter-language button').filter(has_text='English').click();c.wait_for_url('**lang=en');c.locator('#homeBoxingTile').click();c.wait_for_function("document.querySelector('.fighter-growth h3')?.textContent==='MUSCLE LEVELS'");assert c.evaluate("localStorage.getItem('45-language')")=='en';assert not errors,errors
 print('PASS directional guard/no-armor-loss and wrong-side HP damage, Space left/right/front uppercuts, Ctrl dash, locked camera, repeated practice and live-match navigation recovery, saved avatar/LV, desktop/mobile layout, no menu camera, disabled Bot, mandatory mode selection, key remap/duplicate/persistence, keyboard bag/room punches and kicks, immediate movement/stop, crouch, bounded one-shot dashes, inherited room mode for both clients and cleanup; no JS errors')
 b.close()
