"""Local two-player short-jab, gentle evasion and two-second movement regression."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import time
root=__import__('os').environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5055')
out=Path('work/boxing-natural-controls');out.mkdir(parents=True,exist_ok=True)
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
 ca=b.new_context(viewport={'width':1000,'height':850});cb=b.new_context(viewport={'width':390,'height':850});uid,pid,h=account(ca,'Jab');other,opid,oh=account(cb,'Slip')
 ca.request.post(root+'/social/friends',headers=h,data={'action':'request','account_id':other});cb.request.post(root+'/social/friends',headers=oh,data={'action':'accept','account_id':uid})
 a=ca.new_page();c=cb.new_page();errors=[]
 for page in [a,c]:
  page.on('pageerror',lambda e:errors.append(str(e)));page.goto(root+'/45-fitness-coach?lang=en');page.locator('#homeBoxingTile').click();page.wait_for_function("!document.querySelector('[data-mode=friends]').disabled");page.evaluate(pose)
  page.evaluate("Object.assign(testPose[13],{x:.34,y:.46,z:-.10});Object.assign(testPose[15],{x:.35,y:.38,z:-.17});neutralPose=structuredClone(testPose)")
  page.locator('[data-mode=friends]').click();page.locator('[data-control=tracking]').click();page.locator('.fighter-primary').click();page.wait_for_function("document.querySelector('.boxing-status').textContent.includes('Ready')")
 a.get_by_role('button',name='Invite friend',exact=True).click();a.wait_for_function('Boxing.state?.id');c.get_by_role('button',name='Accept invitation',exact=True).click()
 for page in [a,c]:
  page.wait_for_function("Boxing.world?.actors.length===2&&Boxing.world.actors.every(a=>a.canvas.dataset.avatarState==='ready')")
  page.evaluate("const render=Boxing.world.renderer.render.bind(Boxing.world.renderer);let last=0;Boxing.world.renderer.render=(...args)=>{if(performance.now()-last>80){last=performance.now();render(...args)}};void 0")
 a.wait_for_function("Boxing.state.status==='active'",timeout=15000)
 def jab(result,on_impact=None):
  old=a.evaluate('Boxing.state.event?.id||null');a.evaluate('Object.assign(testPose[15],{y:.40,z:-.22})')
  a.wait_for_function('id=>Boxing.state.event&&Boxing.state.event.id!==id',arg=old,timeout=7000)
  assert a.evaluate('Boxing.state.event.result')==result,a.evaluate('Boxing.state.event')
  if on_impact:on_impact()
  event=a.evaluate('Boxing.state.event.id');a.wait_for_timeout(350);assert a.evaluate('Boxing.state.event.id')==event
  a.evaluate('Object.assign(testPose[15],{y:.38,z:-.17})');a.wait_for_timeout(450);assert a.evaluate('Boxing.state.event.id')==event
 # Posture reaches the other client and the opponent rig before any punch event.
 a.evaluate("const angle=.6;for(const i of [0,11,12,13,14,15,16]){const p=testPose[i],x=p.x-.5,z=p.z;p.x=.5+x*Math.cos(angle)+z*Math.sin(angle);p.z=-x*Math.sin(angle)+z*Math.cos(angle)}")
 c.wait_for_function('Math.abs(Boxing.state.players[0].posture?.turn||0)>.45')
 c.wait_for_function('Math.abs(Boxing.world.actors[0].chest.rotation.y)>.25')
 neutral(a);c.wait_for_function('Math.abs(Boxing.world.actors[0].chest.rotation.y)<.04')
 # Brief gentle duck/back sway is evasion, not movement.
 for depth,threshold in [(-.05,'>.24'),(.03,'<-.12')]:
  before=c.evaluate('Boxing.state.players[1].x');c.evaluate('z=>testPose[0].z=z',depth)
  a.wait_for_function('Boxing.state.players[1].bend'+threshold);jab('dodge',lambda:c.evaluate('testPose[0].z=0'));a.wait_for_function('Math.abs(Boxing.state.players[1].bend)<.04')
  assert abs(c.evaluate('Boxing.state.players[1].x')-before)<.03
  assert a.evaluate('Boxing.state.players[1].hp')==10
 jab('hit');jab('hit');assert a.evaluate('Boxing.state.players[1].hp')==8
 # A held lateral lean begins server movement after the new two-second hold.
 start=a.evaluate('Boxing.state.players[0].z');a.evaluate('testPose[0].x-=.06');a.wait_for_function('Boxing.state.players[0].side_since!=null');a.wait_for_timeout(400);assert abs(a.evaluate('Boxing.state.players[0].z')-start)<.03
 a.wait_for_function('z=>Math.abs(Boxing.state.players[0].z-z)>.15',arg=start,timeout=3500)
 z=a.evaluate('Boxing.state.players[0].z');a.evaluate('testPose[0].x=.56');a.wait_for_function('Boxing.state.players[0].side===-1');a.wait_for_function('z=>Boxing.state.players[0].z>z+.10',arg=z,timeout=1700)
 a.evaluate('testPose[0].x=.5');a.wait_for_function('Boxing.state.players[0].side===0');a.wait_for_timeout(300);stopped=a.evaluate('Boxing.state.players[0].z');a.wait_for_timeout(400);assert abs(a.evaluate('Boxing.state.players[0].z')-stopped)<.01
 # Nod plus lateral lean starts diagonal travel; all quadrants switch without a new hold.
 a.evaluate('testPose[0].y+=.06;testPose[0].x=.44')
 a.wait_for_function('Boxing.state.players[0].move===1&&Boxing.state.players[0].side===1',timeout=4500)
 for depth,x,move,side in [(.06,.44,-1,1),(.06,.56,-1,-1),(-.05,.56,1,-1)]:
  a.evaluate('v=>{testPose[0].y=.2;testPose[0].z=v[0];testPose[0].x=v[1]}',[depth,x])
  c.wait_for_function('v=>Boxing.state.players[0].move===v[0]&&Boxing.state.players[0].side===v[1]',arg=[move,side],timeout=1800)
 neutral(a)
 # Acquire visible lower-body landmarks after cropped calibration and synchronize support to the peer.
 a.evaluate("testPose=structuredClone(neutralPose);for(const v of testPose)v.y=v.y*.65+.02;for(const [i,x,y]of [[25,.4,.75],[26,.6,.75],[27,.4,.95],[28,.6,.95]])Object.assign(testPose[i],{x,y,z:0})")
 c.wait_for_function('Boxing.state.players[0].lowerBody?.confidence>.95')
 a.evaluate('testPose[23].x+=.06;testPose[24].x+=.06')
 c.wait_for_function('Boxing.state.players[0].lowerBody?.shiftX<-.3&&Boxing.world.actors[0].supportSmooth.shiftX<-.25')
 a.evaluate('testPose[27].visibility=0')
 c.wait_for_function('Boxing.world.actors[0].supportSmooth.confidence<.01')
 assert not errors,errors
 print('PASS two-client short jabs/rearm, no hold/recoil bonus hits, gentle short duck/back sway without travel, two-second server circling, immediate reversal, neutral stop remote shoulder wind-up, four diagonal directions and synchronized lower-body tracking/fallback')
 b.close()
