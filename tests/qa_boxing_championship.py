"""Local-only end-to-end boxing controls, localization and best-of-three regression."""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time
root='http://127.0.0.1:5055';out=Path('work/championship-review');out.mkdir(exist_ok=True)
def account(c,name):
 assert c.request.post(root+'/auth/register',data={'email':f'champ{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']};r=c.request.post(root+'/profiles',headers=h,data={'name':name+str(time.time_ns())[-5:]});assert r.ok;pid=r.json()['profile']['id'];assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{}}).ok;return c.request.get(root+'/social/me',headers=h).json()['account_id'],pid,h
pose="""window.testPose=Array.from({length:33},()=>({x:.5,y:.5,z:0,visibility:1}));for(const [i,x,y,z]of [[0,.5,.2,0],[11,.35,.4,0],[12,.65,.4,0],[13,.30,.55,-.08],[14,.70,.55,-.08],[15,.4,.3,-.1],[16,.6,.3,-.1],[23,.4,.8,0],[24,.6,.8,0]])Object.assign(testPose[i],{x,y,z});window.neutralPose=structuredClone(testPose);window.LocalPose={ready:true,restart(){},close(){},detect:async()=>({pose:testPose,world:testPose})};const draw=FitnessCharacterRenderer.prototype.draw;FitnessCharacterRenderer.prototype.draw=function(){draw.call(this);if(this.canvas.closest('.boxing-fighters'))this.canvas._fighter=this};window.damageLog=[];new MutationObserver(records=>{for(const r of records)for(const n of r.addedNodes)if(n.classList?.contains('boxing-damage'))damageLog.push(n.textContent)}).observe(document.querySelector('.boxing-effects'),{childList:true});"""
def reset(page):page.evaluate('testPose=structuredClone(neutralPose)');page.wait_for_timeout(550)
def punch(page,side='left',kind='straight'):
 s=11 if side=='left' else 12;e=s+2;h=s+4;sign=1 if side=='left' else -1
 if kind=='uppercut':page.evaluate(f'Object.assign(testPose[{h}],{{x:testPose[{s}].x,y:.62,z:-.07}})');page.wait_for_timeout(500)
 if kind=='straight':code=f'Object.assign(testPose[{e}],{{x:testPose[{s}].x+{sign}*.035,y:.43,z:-.15}});Object.assign(testPose[{h}],{{x:testPose[{s}].x+{sign}*.08,y:.36,z:-.30}})'
 elif kind=='hook':code=f'Object.assign(testPose[{e}],{{x:testPose[{s}].x-({sign})*.13,y:.4,z:-.1}});Object.assign(testPose[{h}],{{x:testPose[{s}].x+{sign}*.20,y:.36,z:-.12}})'
 else:code=f'Object.assign(testPose[{e}],{{x:testPose[{s}].x,y:.54,z:-.13}});Object.assign(testPose[{h}],{{x:testPose[{s}].x,y:.31,z:-.18}})'
 page.evaluate(code)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 ca=b.new_context(viewport={'width':1280,'height':1000});cb=b.new_context(viewport={'width':390,'height':950});uid,pid,h=account(ca,'Blue');other,opid,oh=account(cb,'Red');ca.request.post(root+'/social/friends',headers=h,data={'action':'request','account_id':other});cb.request.post(root+'/social/friends',headers=oh,data={'action':'accept','account_id':uid});a=ca.new_page();c=cb.new_page();errors=[]
 # Software WebGL is capped at 12.5 draws/s; rig updates and camera polling keep their real cadence.
 for page,lang in [(a,'en'),(c,'th')]:
  page.on('pageerror',lambda e:errors.append(str(e)));page.goto(root+'/45-fitness-coach?lang='+lang);page.wait_for_timeout(1000);page.locator('#homeBoxingTile').click();page.wait_for_function("!document.querySelector('[data-mode=practice]').disabled");page.evaluate(pose);page.locator('[data-mode=practice]').click();page.wait_for_function("Boxing.world?.actors[0]?.canvas.dataset.avatarState==='ready'");page.evaluate(pose);page.evaluate("const render=Boxing.world.renderer.render.bind(Boxing.world.renderer);let lastDraw=0;Boxing.world.renderer.render=(...args)=>{const now=performance.now();if(now-lastDraw>80){lastDraw=now;render(...args)}};void 0");page.wait_for_function("/Ready|พร้อม/.test(document.querySelector('.boxing-status').textContent)",timeout=15000)
  assert page.locator('.boxing-clock').is_hidden()
  start_x=page.evaluate('Boxing.world.states[0].x')
  page.evaluate('testPose[0].z=.055');page.wait_for_timeout(3500);assert abs(page.evaluate('Boxing.world.states[0].x')-start_x)<.03
  page.wait_for_function("Boxing.world.states[0].x < -1.35");reset(page)
  page.evaluate('testPose[0].z=-.1');page.wait_for_function("Boxing.world.states[0].x > -1.05");reset(page)
  page.evaluate('for(const i of [0,11,12,13,14,15,16,23,24])testPose[i].y+=.17');page.wait_for_function("Boxing.world.actors[0].body.position.y<-.54");assert page.evaluate('Boxing.world.actors[0].bones.leftLeg.lower.rotation.x')>1
  reset(page);page.wait_for_function("Math.abs(Boxing.world.actors[0].body.position.y+.06)<.04")
  for side,kind in [('right','hook'),('left','uppercut'),('right','straight')]:
   reset(page);n=page.evaluate('damageLog.length');punch(page,side,kind);page.wait_for_function('damageLog.length>'+str(n));assert page.evaluate('Boxing.world.actors[0].punchType')==kind
  assert page.locator('.boxing-bag-damage').inner_text()=='−1 HP';reset(page)
  # One world renderer, profile mesh and actual center bag. Orbit/zoom presets are interactive.
  assert page.locator('.boxing-fighters canvas').count()==1
  assert page.evaluate('Boxing.world.bag.visible&&Boxing.world.bag.position.length()===0')
  page.get_by_role('button',name='Overhead' if lang=='en' else 'มุมสูง',exact=True).click();assert page.evaluate('Boxing.world.mode')=='top'
  page.get_by_role('button',name='Ringside' if lang=='en' else 'ข้างสนาม',exact=True).click()
  rect=page.locator('.cage-canvas').bounding_box();px=rect['x']+rect['width']*.5;py=rect['y']+rect['height']*.6
  page.mouse.move(px,py);page.mouse.down();page.mouse.move(px+45,py-20);page.mouse.up();assert page.evaluate('Boxing.world.mode')=='orbit'
  before=page.evaluate('Boxing.world.distance');page.mouse.wheel(0,-150);page.wait_for_timeout(200);assert page.evaluate('Boxing.world.distance')<before
  page.get_by_role('button',name='Ringside' if lang=='en' else 'ข้างสนาม',exact=True).click()
  # Hide hips/legs: torso still bends and lateral hold moves around the center.
  page.evaluate('testPose[23].visibility=testPose[24].visibility=0;testPose[0].z=-.4');page.wait_for_function('Boxing.world.actors[0].spine.rotation.x>.55');reset(page)
  page.evaluate('testPose[23].visibility=testPose[24].visibility=0;for(const i of [0,11,12,13,14,15,16])testPose[i].x-=.10')
  page.wait_for_function('Boxing.world.actors[0].spine.rotation.z<-.20');page.wait_for_timeout(3500);assert abs(page.evaluate('Boxing.world.states[0].z'))<.05
  page.wait_for_function('Math.abs(Boxing.world.states[0].z)>.25',timeout=6000);page.wait_for_function('Boxing.world.actors[0].gait>.3');page.wait_for_function('Math.abs(Boxing.world.actors[0].bones.leftLeg.upper.rotation.z-.1)>.04');reset(page)
  # Return to the practice starting point via a normal profile selection refresh.
  page.get_by_role('button',name='Disable character control camera' if lang=='en' else 'ปิดกล้องสำหรับควบคุมตัวละคร',exact=True).click()
  page.locator('.boxing-controls select').first.dispatch_event('change');page.wait_for_function("Boxing.world.actors[0]?.canvas.dataset.avatarState==='ready'&&Math.abs(Boxing.world.states[0]?.x+1.05)<.01")
  page.wait_for_function("/Ready|พร้อม/.test(document.querySelector('.boxing-status').textContent)",timeout=15000)

  assert page.locator('.boxing-vitals').first.evaluate('n=>getComputedStyle(n).backgroundColor')=='rgba(0, 0, 0, 0)'
  page.locator('.boxing-expand').click();page.wait_for_function("document.fullscreenElement||document.querySelector('.boxing-expanded')");assert page.locator('.boxing-arena').bounding_box()['width']>=page.viewport_size['width']-2;page.locator('.boxing-expand').click();page.wait_for_function("!document.fullscreenElement&&!document.querySelector('.boxing-expanded')")
  page.evaluate("document.querySelector('.boxing-arena').requestFullscreen=undefined");page.locator('.boxing-expand').click();page.wait_for_selector('.boxing-expanded');page.keyboard.press('Escape');page.wait_for_function("!document.querySelector('.boxing-expanded')")
  page.evaluate("document.body.dataset.effects='on'");before=page.evaluate('Boxing.world.beams[0].rotation.z');page.wait_for_timeout(350);assert page.evaluate('Boxing.world.beams[0].rotation.z')!=before
  page.emulate_media(reduced_motion='reduce');page.wait_for_function('Boxing.world.beams[0].rotation.z===0');page.emulate_media(reduced_motion='no-preference')
  if lang=='en':assert not __import__('re').search('[ก-๙]',page.locator('#boxingPage').inner_text()),page.locator('#boxingPage').inner_text()
  print(lang,'PASS gentle backward/forward, crouch/stand rig, assisted types, bag damage, native/fallback fullscreen, transparent HUD and moving/reduced-motion arena',flush=True)
 for page in [a,c]:
  page.locator('.boxing-back').click();page.wait_for_function("!document.querySelector('[data-mode=friends]').disabled");page.locator('[data-mode=friends]').click();page.wait_for_function("/Ready|พร้อม/.test(document.querySelector('.boxing-status').textContent)")
 a.get_by_role('button',name='Invite friend',exact=True).click();a.wait_for_function('Boxing.state?.id');c.wait_for_selector('.boxing-rooms button');c.get_by_role('button',name='รับคำชวน',exact=True).click()
 for page in [a,c]:
  page.wait_for_function('Boxing.state?.players.length===2&&Boxing.world?.actors.length===2');page.evaluate("const render=Boxing.world.renderer.render.bind(Boxing.world.renderer);let last=0;Boxing.world.renderer.render=(...args)=>{if(performance.now()-last>80){last=performance.now();render(...args)}};void 0")
 a.wait_for_function("Boxing.state.status==='active'",timeout=12000);assert a.locator('.boxing-clock').is_visible();assert a.evaluate('!Boxing.world.bag.visible&&Boxing.world.actors.length===2');initial=a.locator('.boxing-clock strong').inner_text();a.wait_for_function("old=>document.querySelector('.boxing-clock strong').textContent!==old",arg=initial,timeout=5000)
 c.evaluate('for(const i of [0,11,12,13,14,15,16,23,24])testPose[i].y+=.17');a.wait_for_function('Boxing.state.players[1].crouch>.9');a.wait_for_function("Boxing.world.actors[1].body.position.y<-.51");reset(c);a.wait_for_function('Boxing.state.players[1].crouch<.05')
 # Correct-side slip avoids a real timed punch; recovery does not add a second strike.
 c.evaluate('testPose[0].x+=.12');c.wait_for_function('Boxing.world.states[1].slip<-.6');a.wait_for_function('Boxing.state.players[1].slip<-.6');punch(a,'left');a.wait_for_function("Boxing.state.event?.result==='dodge'",timeout=7000);assert a.evaluate('Boxing.state.players[1].hp')==10
 reset(a);reset(c);n=a.evaluate('Boxing.state.events.length');a.wait_for_timeout(900);assert a.evaluate('Boxing.state.events.length')==n
 # Split the first two rounds, then win the deciding third, using the actual pose loop.
 for round_number,attacker,target in [(1,a,1),(2,c,0),(3,a,1)]:
  attacker.wait_for_function(f"Boxing.state.status==='active'&&Boxing.state.round==={round_number}",timeout=12000)
  for hit in range(10):
   reset(attacker);punch(attacker,'right','straight')
   attacker.wait_for_function(f"Boxing.state.players[{target}].hp<={9-hit}",timeout=7000)
  for page in [a,c]:page.wait_for_function("Boxing.state.status==="+repr('finished' if round_number==3 else 'round_break'))
  if round_number<3:
   for page in [a,c]:
    page.wait_for_function("/Round over|จบยก/.test(document.querySelector('.boxing-banner').textContent)");page.wait_for_timeout(400);assert page.locator('.boxing-banner').inner_text()
   assert ca.request.get(root+f'/social/boxing/trophies/{pid}',headers=h).json()['trophies']==0
   a.wait_for_function(f"Boxing.state.round==={round_number+1}",timeout=10000);assert a.evaluate('Boxing.state.players.every(p=>p.hp===10&&p.armor===10)')
  print('round',round_number,'PASS',flush=True)
 assert a.evaluate('Boxing.state.winner')==uid;assert a.evaluate('Boxing.state.players.map(p=>p.wins)')==[2,1];assert ca.request.get(root+f'/social/boxing/trophies/{pid}',headers=h).json()['trophies']==1
 frozen=a.locator('.boxing-clock strong').inner_text();a.wait_for_timeout(1200);assert a.locator('.boxing-clock strong').inner_text()==frozen
 for page,width in [(a,1280),(c,390)]:
  page.evaluate('FitnessCharacterRenderer.prototype.schedule=()=>{}');page.add_style_tag(content='.boxing-ambience i{animation:none!important}');page.screenshot(path=str(out/f'{width}-championship.png'));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
 assert not errors,errors;print('PASS both-client crouch sync, three rounds 2–1, resets, clock and single final trophy; no JS errors',flush=True);b.close()
