"""Local-only camera-loop regression using synthetic poses and Chromium's fake stream."""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time
root='http://127.0.0.1:5055';out=Path('work/boxing-practice-review');out.mkdir(exist_ok=True)
def account(c,name):
 assert c.request.post(root+'/auth/register',data={'email':f'practice{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']};r=c.request.post(root+'/profiles',headers=h,data={'name':name+str(time.time_ns())[-6:]});assert r.ok;pid=r.json()['profile']['id'];assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{}}).ok;return c.request.get(root+'/social/me',headers=h).json()['account_id'],pid,h
pose="""window.testPose=Array.from({length:33},()=>({x:.5,y:.5,z:0,visibility:1}));for(const [i,x,y,z]of [[0,.5,.2,0],[11,.35,.4,0],[12,.65,.4,0],[13,.30,.55,-.08],[14,.70,.55,-.08],[15,.4,.3,-.1],[16,.6,.3,-.1],[23,.4,.8,0],[24,.6,.8,0]])Object.assign(testPose[i],{x,y,z});window.LocalPose={ready:true,restart(){},close(){},detect:async()=>({pose:testPose,world:testPose})};const update=CageFighter.prototype.update;CageFighter.prototype.update=function(...args){update.apply(this,args);this.maxReach=Math.max(this.maxReach||1,this.bones?.leftArm?.upper.scale.x||1)};window.damageLog=[];new MutationObserver(records=>{for(const r of records)for(const n of r.addedNodes)if(n.classList?.contains('boxing-damage'))damageLog.push({text:n.textContent,type:n.className,left:n.style.left})}).observe(document.querySelector('.boxing-effects'),{childList:true});"""
def bend(page):
 page.evaluate("Object.assign(testPose[13],{x:.30,y:.55,z:-.08});Object.assign(testPose[15],{x:.4,y:.3,z:-.1})");page.wait_for_timeout(550)
def punch(page):
 page.evaluate("Object.assign(testPose[13],{x:.35,y:.4,z:-.20});Object.assign(testPose[15],{x:.35,y:.4,z:-.46})")
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 a=b.new_context(viewport={'width':1280,'height':1000});c=b.new_context(viewport={'width':390,'height':1000});uid,pid,h=account(a,'Blue');other,opid,oh=account(c,'Peach');a.request.post(root+'/social/friends',headers=h,data={'action':'request','account_id':other});c.request.post(root+'/social/friends',headers=oh,data={'action':'accept','account_id':uid})
 pa=a.new_page();pb=c.new_page();errors=[]
 for page in [pa,pb]:
  page.on('pageerror',lambda e:errors.append(str(e)));page.goto(root+'/45-fitness-coach');page.wait_for_timeout(900);page.locator('#homeBoxingTile').click();page.wait_for_function("Boxing.world?.actors[0]?.canvas.dataset.avatarState==='ready'");assert page.evaluate('Boxing.world.bag.visible');page.evaluate(pose);page.get_by_role('button',name='เปิดกล้องสำหรับควบคุมตัวละคร',exact=True).click();page.wait_for_function("document.querySelector('.boxing-status').textContent.includes('พร้อม')",timeout=15000);assert page.locator('.boxing-preview').is_hidden()
  # Walking is independent of hands and works in the solo practice arena.
  page.evaluate('testPose[15].visibility=testPose[16].visibility=.1;testPose[0].z=-.16');page.wait_for_function("Boxing.world.states[0].x>-.85")
  page.evaluate('testPose[0].z=.16');page.wait_for_function("Boxing.world.states[0].x<-1.1")
  page.evaluate('testPose[0].z=0;testPose[15].visibility=testPose[16].visibility=1');page.wait_for_timeout(700);pos=page.evaluate('Boxing.world.states[0].x');page.wait_for_timeout(450);assert abs(page.evaluate('Boxing.world.states[0].x')-pos)<.03
  bend(page);punch(page);page.wait_for_function('damageLog.some(x=>x.text==="−1")');page.wait_for_function('Boxing.world.actors[0].maxReach>1.01');page.wait_for_function('Boxing.world.actors[0].bones.leftArm.upper.scale.x===1')
  count=page.evaluate('damageLog.length');page.wait_for_timeout(600);assert page.evaluate('damageLog.length')==count
  bend(page);page.evaluate('testPose[0].z=.16');page.wait_for_function("Boxing.world.states[0].x<-1.9");page.evaluate('testPose[0].z=0');page.wait_for_timeout(550);punch(page);page.wait_for_function('damageLog.some(x=>x.text==="ไม่ถึง")');bend(page)
  page.evaluate('testPose[0].z=-.16');page.wait_for_function("Boxing.world.states[0].x>-1.1");page.evaluate('testPose[0].z=0');page.wait_for_timeout(550)
  assert page.locator('.boxing-hud progress').first.get_attribute('value')=='10';assert c.request.get(root+f'/social/boxing/trophies/{opid}',headers=oh).json()['trophies']==0
  page.evaluate("FitnessCharacterRenderer.prototype.schedule=()=>{}");page.screenshot(path=str(out/f'{page.viewport_size["width"]}-practice.png'));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2');print(page.viewport_size['width'],'PASS practice movement/neutral, hidden hands, hit/miss, extension/retraction, no held duplicates',flush=True)
 pa.get_by_role('button',name='ชวนเพื่อน',exact=True).click();pa.wait_for_function('Boxing.state?.id');mid=pa.evaluate('Boxing.state.id');assert pa.evaluate('Boxing.world.bag.visible');pb.wait_for_selector('.boxing-rooms button');pb.get_by_role('button',name='รับคำชวน',exact=True).click()
 for page in [pa,pb]:
  page.wait_for_function('Boxing.state?.players.length===2');assert page.evaluate('!Boxing.world.bag.visible');page.get_by_role('button',name='พร้อม',exact=True).click()
 pa.wait_for_function("Boxing.state.status==='active'",timeout=10000);pa.evaluate('damageLog=[]');pb.evaluate('damageLog=[]');pa.evaluate('testPose[0].z=-.16');pa.wait_for_function('Boxing.state.players[0].x>-.5');pb.wait_for_function('Boxing.state.players[0].x>-.5');pa.evaluate('testPose[0].z=.16');pa.wait_for_function('Boxing.state.players[0].x<-.85');pa.evaluate('testPose[0].z=0');pa.wait_for_timeout(600)
 pa.evaluate('testPose[0].z=-.08');pa.wait_for_function('Boxing.state.players[0].x>-.5');pa.evaluate('testPose[0].z=0');pa.wait_for_timeout(550)
 bend(pa);punch(pa)
 for page in [pa,pb]:page.wait_for_function('damageLog.some(x=>x.text==="−1")');page.wait_for_function('Boxing.state.players[1].hp===9')
 pa.wait_for_timeout(500);assert pa.evaluate('damageLog.filter(x=>x.text==="−1").length')==1;assert pb.evaluate('damageLog.filter(x=>x.text==="−1").length')==1
 bend(pa);pb.evaluate('testPose[13].y=testPose[14].y=.4');pb.wait_for_function('Boxing.state.players[1].guard_until>Date.now()/1000',timeout=10000);punch(pa)
 for page in [pa,pb]:page.wait_for_function('damageLog.some(x=>x.text==="เกราะ −1")');page.wait_for_function('Boxing.state.players[1].armor===9');assert page.evaluate('Boxing.state.players[1].hp')==9
 assert not errors,errors;print('PASS two-client movement, server damage popups once per event, guard damage, bag hidden in match, no JS errors',flush=True)
 pa.get_by_role('button',name='ออกจากแมตช์',exact=True).click();pa.wait_for_function('Boxing.state===null');assert pa.evaluate('Boxing.world.bag.visible');assert pa.evaluate("document.querySelector('.boxing-preview video').srcObject===null");b.close()
