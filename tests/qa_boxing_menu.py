"""Local-only mode entry, camera lifecycle and automatic friend-match regression."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import time
root=__import__('os').environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5055')
out=Path('work/boxing-menu-review');out.mkdir(exist_ok=True)
def account(c,name):
 assert c.request.post(root+'/auth/register',data={'email':f'menu{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']}
 pid=c.request.post(root+'/profiles',headers=h,data={'name':name+str(time.time_ns())[-4:]}).json()['profile']['id']
 assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{}}).ok
 return c.request.get(root+'/social/me',headers=h).json()['account_id'],pid,h
pose="""window.testPose=Array.from({length:33},()=>({x:.5,y:.5,z:0,visibility:1}));for(const [i,x,y,z]of [[0,.5,.2,0],[11,.35,.4,0],[12,.65,.4,0],[13,.30,.55,-.08],[14,.70,.55,-.08],[15,.4,.3,-.1],[16,.6,.3,-.1],[23,.4,.8,0],[24,.6,.8,0]])Object.assign(testPose[i],{x,y,z});window.neutralPose=structuredClone(testPose);window.LocalPose={ready:true,restart(){},close(){},detect:async()=>({pose:testPose,world:testPose})};"""
def neutral(p):p.evaluate('testPose=structuredClone(neutralPose)');p.wait_for_timeout(600)
def punch(p):p.evaluate('Object.assign(testPose[14],{x:.615,y:.43,z:-.15});Object.assign(testPose[16],{x:.57,y:.36,z:-.30})')
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-background-timer-throttling','--disable-renderer-backgrounding','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 ca=b.new_context(viewport={'width':1280,'height':1050});cb=b.new_context(viewport={'width':390,'height':950})
 uid,pid,h=account(ca,'Blue');other,opid,oh=account(cb,'Red')
 assert ca.request.post(root+'/social/friends',headers=h,data={'action':'request','account_id':other}).ok
 assert cb.request.post(root+'/social/friends',headers=oh,data={'action':'accept','account_id':uid}).ok
 a=ca.new_page();c=cb.new_page();errors=[]
 for page,lang in [(a,'en'),(c,'th')]:
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(root+'/45-fitness-coach?lang='+lang);page.locator('#homeBoxingTile').click();page.wait_for_function("!document.querySelector('[data-mode=practice]').disabled")
  assert page.locator('.boxing-menu').is_visible();assert page.locator('.boxing-mode-card').count()==4
  assert page.locator('.boxing-arena').is_hidden();assert page.evaluate('Boxing.world===null&&document.querySelector(".boxing-preview video").srcObject===null')
  page.wait_for_timeout(1000);page.locator('.boxing-menu').screenshot(path=str(out/f'menu-{page.viewport_size["width"]}.png'))
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  page.evaluate(pose)
  page.locator('[data-mode=practice]').click();page.locator('[data-control=tracking]').click();page.locator('.fighter-primary').click();page.wait_for_function("Boxing.world?.actors[0]?.canvas.dataset.avatarState==='ready'")
  # Cap only software rasterization, preserving production rig and camera cadence.
  page.evaluate("const draw=BoxingWorld.prototype.tick;const render=Boxing.world.renderer.render.bind(Boxing.world.renderer);let last=0;Boxing.world.renderer.render=(...args)=>{if(performance.now()-last>80){last=performance.now();render(...args)}};void 0")
  page.wait_for_function("/Ready|พร้อม/.test(document.querySelector('.boxing-status').textContent)")
  assert page.locator('.boxing-clock').is_hidden();assert page.evaluate('Boxing.world.bag.visible')
  punch(page);page.wait_for_function('document.querySelector(".boxing-bag-damage").textContent.includes("1")');neutral(page)
  page.locator('.boxing-back').click();page.wait_for_function("Boxing.mode==='menu'&&Boxing.world===null")
  assert page.evaluate('document.querySelector(".boxing-preview video").srcObject===null')
  page.wait_for_function("!document.querySelector('[data-mode=friends]').disabled");page.locator('[data-mode=friends]').click();page.locator('[data-control=tracking]').click();page.locator('.fighter-primary').click()
  page.wait_for_function("/Ready|พร้อม/.test(document.querySelector('.boxing-status').textContent)")
  assert page.locator('.boxing-lobby').is_visible();assert page.locator('.boxing-arena').is_hidden();assert page.evaluate('Boxing.world===null')
  print(lang,'PASS menu, practice entry/hit, camera cleanup, friend lobby; no early arena',flush=True)
 c.locator('.boxing-back').click();c.wait_for_function("Boxing.mode==='menu'&&Boxing.world===null")
 a.get_by_role('button',name='Invite friend',exact=True).click();a.wait_for_function("Boxing.state?.status==='invited'")
 assert a.locator('.boxing-arena').is_hidden();assert a.locator('.boxing-lobby').is_visible()
 c.evaluate('id=>Boxing.invitation(id)',a.evaluate('Boxing.state.id'));c.wait_for_function("Boxing.mode==='friends'")
 c.get_by_role('button',name='รับคำชวน',exact=True).click()
 for p in [a,c]:
  p.wait_for_function("Boxing.state?.status==='countdown'||Boxing.state?.status==='active'",timeout=15000)
  p.wait_for_function("Boxing.world?.actors.length===2&&Boxing.world.actors.every(a=>a.canvas.dataset.avatarState==='ready')")
  assert p.locator('.boxing-lobby').is_hidden();assert not p.evaluate('Boxing.world.bag.visible')
  p.evaluate("const render=Boxing.world.renderer.render.bind(Boxing.world.renderer);let last=0;Boxing.world.renderer.render=(...args)=>{if(performance.now()-last>80){last=performance.now();render(...args)}};void 0")
 a.wait_for_function("Boxing.state.status==='active'",timeout=15000)
 assert a.locator('.boxing-clock').is_visible();initial=a.locator('.boxing-clock strong').inner_text()
 a.wait_for_function("v=>document.querySelector('.boxing-clock strong').textContent!==v",arg=initial)
 punch(a);a.wait_for_function('Boxing.state.players[1].hp===9',timeout=10000);c.wait_for_function('Boxing.state.players[1].hp===9');neutral(a)
 for p in [a,c]:p.locator('.boxing-arena').screenshot(path=str(out/f'match-{p.viewport_size["width"]}.png'))
 a.locator('.boxing-back').click();a.wait_for_function("Boxing.mode==='menu'&&Boxing.state===null&&Boxing.world===null")
 assert a.evaluate('document.querySelector(".boxing-preview video").srcObject===null')
 c.wait_for_function("Boxing.state.status==='finished'")
 assert not errors,errors
 print('PASS invitation, auto-ready/countdown, two-client damage, match clock, leave cleanup and no JS errors',flush=True)
 # Camera denial leaves a usable practice page and the menu remains camera-free.
 cd=b.new_context(viewport={'width':390,'height':950});account(cd,'Solo');d=cd.new_page();d.on('pageerror',lambda e:errors.append(str(e)))
 d.goto(root+'/45-fitness-coach?lang=en');d.locator('#homeBoxingTile').click();d.wait_for_function("!document.querySelector('[data-mode=practice]').disabled")
 d.evaluate("navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Camera permission denied','NotAllowedError')};void 0")
 d.locator('[data-mode=practice]').click();d.locator('[data-control=tracking]').click();d.locator('.fighter-primary').click();d.wait_for_function("document.querySelector('.boxing-status').textContent.includes('denied')")
 assert d.locator('.boxing-arena').is_visible();assert d.get_by_role('button',name='Enable character control camera',exact=True).is_visible()
 d.locator('.boxing-back').click();d.wait_for_function("Boxing.mode==='menu'&&!document.querySelector('[data-mode=friends]').disabled")
 d.locator('[data-mode=friends]').click();d.locator('[data-control=tracking]').click();d.locator('.fighter-primary').click();d.wait_for_function("document.querySelector('.boxing-status').textContent.includes('denied')")
 assert d.get_by_role('button',name='Open friends',exact=True).is_visible();assert d.get_by_role('button',name='Invite friend',exact=True).is_disabled()
 d.locator('.boxing-back').click();d.wait_for_function("Boxing.mode==='menu'&&Boxing.world===null")
 assert not errors,errors
 print('PASS permission denial, retry camera control, empty friend list and return to menu',flush=True)
 b.close()
