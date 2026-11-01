"""Local camera fixture: tracked player versus an animated server-owned bot."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import ast,os,time
root=os.environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5071');assert root.startswith('http://127.0.0.1:')
source=ast.parse(Path('tests/qa_boxing_championship.py').read_text());pose=next(ast.literal_eval(n.value) for n in source.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='pose' for t in n.targets))
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 c=b.new_context(viewport={'width':1000,'height':850});assert c.request.post(root+'/auth/register',data={'email':f'trackbot{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']};pid=c.request.post(root+'/profiles',headers=h,data={'name':'Camera Bot '+str(time.time_ns())[-5:]}).json()['profile']['id'];assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{}}).ok
 p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(root+'/45-fitness-coach?lang=en');p.locator('#homeBoxingTile').click();p.wait_for_function("!document.querySelector('[data-mode=bot]').disabled");p.evaluate(pose)
 p.locator('[data-mode=bot]').click();p.locator('[data-control=tracking]').click();p.locator('.fighter-primary').click();p.wait_for_function("Boxing.state?.status==='active'",timeout=25000)
 p.wait_for_function("Boxing.world?.actors.length===2&&Boxing.world.actors.every(a=>a.body)",timeout=60000)
 assert p.evaluate("Boxing.world.states[0].controlMode==='tracking'&&Boxing.world.states[1].controlMode==='computer'")
 p.wait_for_function('Boxing.state.players[1].last_punch>0',timeout=7000);before=p.evaluate('Boxing.state.players[0].last_punch');p.keyboard.press('q');p.wait_for_timeout(200);assert p.evaluate('Boxing.state.players[0].last_punch')==before
 p.evaluate("Object.assign(testPose[13],{x:.385,y:.43,z:-.15});Object.assign(testPose[15],{x:.43,y:.36,z:-.30})")
 p.wait_for_function('t=>Boxing.state.players[0].last_punch>t',arg=before,timeout=3000);assert p.evaluate("Boxing.state.players[0].punch_type==='hook'")
 p.locator('.boxing-back').click();p.wait_for_function("Boxing.mode==='menu'&&document.querySelector('.boxing-preview video').srcObject===null");assert not errors,errors
 print('PASS camera calibration/ready, tracked hook, disabled keyboard attacks, animated autonomous bot and camera cleanup')
 b.close()
