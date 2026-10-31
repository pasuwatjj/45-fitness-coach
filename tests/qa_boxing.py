from playwright.sync_api import sync_playwright
from pathlib import Path
import time
root='http://127.0.0.1:5055';out=Path('work/boxing-review');out.mkdir(exist_ok=True)
def account(c,name):
 assert c.request.post(root+'/auth/register',data={'email':f'box{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 token=c.request.post(root+'/session').json()['session_token'];h={'X-Coach-Session':token};r=c.request.post(root+'/profiles',headers=h,data={'name':name+str(time.time_ns())[-6:]});assert r.ok,r.text();pid=r.json()['profile']['id']
 r=c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{'hair_color':'#634473'}});assert r.ok,r.text();uid=c.request.get(root+'/social/me',headers=h).json()['account_id'];return uid,pid,h
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 a=b.new_context(viewport={'width':1280,'height':1000});c=b.new_context(viewport={'width':390,'height':1000});uid,pid,h=account(a,'Blue Boxer');other,opid,oh=account(c,'Peach Boxer')
 a.request.post(root+'/social/friends',headers=h,data={'action':'request','account_id':other});c.request.post(root+'/social/friends',headers=oh,data={'action':'accept','account_id':uid})
 print('Accounts and friendship ready',flush=True);pa=a.new_page();pb=c.new_page();errors=[]
 for page in [pa,pb]:
  page.on('pageerror',lambda e:errors.append(str(e)));page.goto(root+'/45-fitness-coach');page.wait_for_timeout(1000);page.locator('#homeBoxingTile').click();page.wait_for_selector('#boxingPage canvas[data-avatar-state=ready]',timeout=30000)
  assert page.locator('.boxing-preview').is_hidden()
 print('Both saved avatars loaded',flush=True);pa.get_by_role('button',name='ชวนเพื่อน',exact=True).click();pb.evaluate("setTab('inbox')");pb.wait_for_selector('.inbox-thread');pb.locator('.inbox-thread').click();pb.get_by_role('button',name='เปิดคำชวน Boxing',exact=True).click();pb.wait_for_selector('.boxing-rooms button');pb.get_by_role('button',name='รับคำชวน',exact=True).click()
 for page in [pa,pb]:
  page.wait_for_function("Boxing.state?.players.length===2");page.wait_for_selector('#boxingPage canvas[data-avatar-state=ready]');page.wait_for_timeout(1000)
  assert page.locator('.boxing-fighters canvas').count()==2;assert page.locator('.boxing-rooms button').count()==0
  # Simulate confident upper-body landmarks; camera stream itself remains a real browser MediaStream.
  page.evaluate("""window.testPose=Array.from({length:33},()=>({x:.5,y:.5,z:0,visibility:1}));Object.assign(testPose[0],{x:.5,y:.2});Object.assign(testPose[11],{x:.35,y:.4});Object.assign(testPose[12],{x:.65,y:.4});Object.assign(testPose[13],{x:.28,y:.55});Object.assign(testPose[14],{x:.72,y:.55});Object.assign(testPose[15],{x:.4,y:.3});Object.assign(testPose[16],{x:.6,y:.3});window.LocalPose={ready:true,restart(){},close(){},detect:async()=>({pose:testPose,world:testPose})};""")
  page.get_by_role('button',name='เปิดกล้องสำหรับควบคุมตัวละคร',exact=True).click();page.wait_for_timeout(2500);assert page.locator('.boxing-preview').is_hidden();page.get_by_role('button',name='แสดงภาพตัวเอง',exact=True).click();assert page.locator('.boxing-preview').is_visible();page.get_by_role('button',name='ซ่อนภาพตัวเอง',exact=True).click();assert page.evaluate("document.querySelector('.boxing-preview video').srcObject.getVideoTracks()[0].readyState==='live'")
  page.get_by_role('button',name='พร้อม',exact=True).click()
 print('Both ready',flush=True);pa.wait_for_function("['countdown','active'].includes(Boxing.state.status)");pa.wait_for_function("Boxing.state.status==='active'",timeout=9000)
 pb.evaluate("testPose[15].y=.65;testPose[16].y=.65");pb.wait_for_timeout(700);pa.evaluate("Object.assign(testPose[13],{x:.35,y:.4,z:-.18});Object.assign(testPose[15],{x:.35,y:.4,z:-.4})");pb.wait_for_function("Boxing.state.players[1].hp===9");pa.wait_for_function("Boxing.state.players[1].hp===9");print('Camera-derived punch synchronized on both clients',flush=True)
 pa.evaluate("testPose[15].y=.75;testPose[15].z=0");pa.wait_for_function("Boxing.state.players[0].arms?.left.lower[1]<-.5");pb.wait_for_function("Boxing.state.players[0].arms?.left.lower[1]<-.5")
 pb.evaluate("testPose[11].z=.1;testPose[12].z=.1");pb.wait_for_function("Boxing.state.players[1].position>.72");assert pb.evaluate('Boxing.state.players[1].armor')==10
 pb.evaluate("testPose[11].z=0;testPose[12].z=0;testPose[13].y=.4;testPose[14].y=.4");pb.wait_for_function("Boxing.state.players[1].guard_until>Date.now()/1000",timeout=10000);pb.wait_for_selector('.boxing-vitals.guard-active')
 print('PASS lowered arms sync, backward movement without armor cost, held elbow guard activates blue',flush=True)
 print('Match active',flush=True)
 for page,width in [(pa,1280),(pb,390)]:
  page.evaluate("FitnessCharacterRenderer.prototype.schedule=()=>{}");page.locator('.boxing-arena').evaluate("n=>n.scrollIntoView({block:'center'})");page.screenshot(path=str(out/f'{width}-arena.png'),timeout=120000);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2');print(width,'captured',flush=True)
 pa.evaluate("setTab('home')");assert pa.evaluate("document.querySelector('.boxing-preview video').srcObject===null");pb.wait_for_function("Boxing.state.status==='finished'");assert pb.evaluate('Boxing.state.winner')==other
 pb.evaluate("setTab('profile')");pb.wait_for_selector('.profile-metric');pb.wait_for_function("[...document.querySelectorAll('.profile-metric')].some(n=>n.textContent.includes('ถ้วยแชมป์ Boxing')&&n.querySelector('strong').textContent==='1')");pb.reload();pb.wait_for_timeout(900);pb.evaluate("setTab('profile')");pb.wait_for_function("[...document.querySelectorAll('.profile-metric')].some(n=>n.textContent.includes('ถ้วยแชมป์ Boxing')&&n.querySelector('strong').textContent==='1')");print('PASS trophy visible on profile and persists after reload',flush=True)
 assert not errors,errors;print('PASS two accounts, saved avatars, invitation, acceptance, hidden preview/live camera, readiness/countdown, disconnect, responsive arena, no JS errors');b.close()
