"""Local camera fixtures: manual lock in workout, cardio, and boxing views."""
import os,time,ast
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];assert root.startswith('http://127.0.0.1:')
source=ast.parse(Path('tests/qa_boxing_championship.py').read_text());fixture=next(ast.literal_eval(n.value) for n in source.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='pose' for t in n.targets))
out=Path('work/tracking-lock-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 c=b.new_context(viewport={'width':1200,'height':1000});assert c.request.post(root+'/auth/register',data={'email':f'lock{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']};pid=c.request.post(root+'/profiles',headers=h,data={'name':'Tracking lock '+str(time.time_ns())[-6:]}).json()['profile']['id'];assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{}}).ok
 p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(root+'/45-fitness-coach?lang=en');p.evaluate(fixture)
 p.evaluate("window.poseRows=[testPose];LocalPose.start=()=>{};LocalPose.detect=async()=>({width:640,height:480,pose:poseRows[0]||[],world:poseRows[0]||[],poses:poseRows,worlds:poseRows,hands:[],handWorld:[]});void 0")
 p.evaluate("setTab('workout')");p.locator('#start').click();p.wait_for_function("fitnessState.running&&fitnessState.tracking.status[0]==='locked'",timeout=25000)
 pin=p.locator('.tracking-pin-controls button').first;pin.click();p.wait_for_function('fitnessState.tracking.pinned[0]===true');assert pin.get_attribute('aria-pressed')=='true';sid=p.evaluate('fitnessState.set_id');before=p.evaluate('fitnessState.reps')
 p.evaluate("testPose.forEach(v=>v.x+=.04)");p.wait_for_timeout(900);assert p.evaluate('fitnessState.tracking.status[0]')=='locked';assert p.evaluate('fitnessState.set_id')==sid;assert p.evaluate('fitnessState.reps')==before
 p.locator('.tracking-pin-controls').screenshot(path=str(out/'workout-lock.png'))
 p.evaluate('poseRows=[]');p.wait_for_function("fitnessState.tracking.status[0]!=='locked'",timeout=5000);assert p.evaluate('fitnessState.tracking.pinned[0]===true');lost=p.evaluate('fitnessState.reps');p.wait_for_timeout(500);assert p.evaluate('fitnessState.reps')==lost
 p.evaluate('poseRows=[testPose]');p.wait_for_function("fitnessState.tracking.status[0]==='locked'",timeout=5000);pin.click();p.wait_for_function('fitnessState.tracking.pinned[0]===false')
 p.locator('#stop').click();p.wait_for_function('!fitnessState.running');p.evaluate("setTab('cardio')");p.get_by_role('button',name='▶ Open camera and start',exact=True).click();p.wait_for_function("fitnessState.cardio&&fitnessState.tracking.status[0]==='locked'",timeout=25000);pin.click();p.wait_for_function('fitnessState.tracking.pinned[0]===true');assert p.locator('#cardioPage .tracking-pin-controls').is_visible();p.locator('.tracking-pin-controls').screenshot(path=str(out/'cardio-lock.png'))
 p.evaluate("setTab('boxing')");p.wait_for_function("!document.querySelector('[data-mode=practice]').disabled");p.locator('[data-mode=practice]').click();p.locator('[data-control=tracking]').click();p.locator('.fighter-primary').click()
 boxpin=p.locator('#boxingPage .tracking-lock-button');boxpin.wait_for();p.wait_for_function("!document.querySelector('#boxingPage .tracking-lock-button').disabled",timeout=20000);boxpin.click();assert boxpin.get_attribute('aria-pressed')=='true'
 p.evaluate("window.bystander=testPose.map(v=>({...v,x:v.x+.8}));poseRows=[bystander,testPose]");p.wait_for_timeout(900);assert 'Keep moving naturally' in p.locator('#boxingPage .tracking-lock-status').inner_text()
 p.evaluate('poseRows=[]');p.wait_for_function("document.querySelector('#boxingPage .tracking-lock-status').textContent.includes('Waiting')",timeout=3000);assert boxpin.get_attribute('aria-pressed')=='true'
 p.evaluate('poseRows=[testPose]');p.wait_for_function("document.querySelector('#boxingPage .tracking-lock-status').textContent.includes('Keep moving')",timeout=6000)
 p.locator('.boxing-controls').screenshot(path=str(out/'boxing-lock.png'));boxpin.click();assert boxpin.get_attribute('aria-pressed')=='false';p.locator('.boxing-back').click();assert not errors,errors
 print('PASS workout/cardio/boxing lock buttons, preserved set/counts, moving target and reordered bystander, blank-frame pause without stale reps, nearby reacquisition, explicit unlock and camera cleanup')
 b.close()
