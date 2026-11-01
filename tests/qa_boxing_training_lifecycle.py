"""Local tracking-mode auto, hidden-tab stop and page-exit hit persistence."""
from playwright.sync_api import sync_playwright
import os,time
root=os.environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5073');assert root.startswith('http://127.0.0.1:')
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 c=b.new_context();assert c.request.post(root+'/auth/register',data={'email':f'autolife{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']};pid=c.request.post(root+'/profiles',headers=h,data={'name':'Auto lifecycle '+str(time.time_ns())[-5:]}).json()['profile']['id'];assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{}}).ok
 p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(root+'/45-fitness-coach?lang=en');p.locator('#homeBoxingTile').click();p.wait_for_function("!document.querySelector('[data-mode=practice]').disabled")
 p.evaluate("navigator.mediaDevices.getUserMedia=async()=>{throw Error('Camera intentionally unavailable')};void 0");p.locator('[data-mode=practice]').click();p.locator('[data-control=tracking]').click();p.locator('.fighter-primary').click();p.wait_for_function("!document.querySelector('.boxing-training button').disabled&&Boxing.world?.actors[0]?.body",timeout=60000)
 auto=p.locator('.boxing-training button').first;auto.click();p.wait_for_function("document.querySelector('.boxing-training strong').textContent==='MAX HP 12'",timeout=15000);assert p.evaluate("Boxing.world.states[0].controlMode==='computer'&&Boxing.controlMode==='tracking'")
 p.evaluate("Object.defineProperty(document,'hidden',{get:()=>true,configurable:true});document.dispatchEvent(new Event('visibilitychange'));void 0");assert auto.get_attribute('aria-pressed')=='false';p.wait_for_timeout(1000)
 before=c.request.get(root+f'/social/boxing/training/{pid}',headers=h).json()['total_hits'];p.wait_for_timeout(1000);assert c.request.get(root+f'/social/boxing/training/{pid}',headers=h).json()['total_hits']==before
 p.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));void 0");p.wait_for_function("!document.querySelector('.boxing-training button').disabled&&Boxing.world.running");assert auto.get_attribute('aria-pressed')=='false'
 # Reload immediately after a new bag hit, before the regular batch timer fires.
 stamp=p.evaluate('performance.now()');auto.click();p.wait_for_function('v=>Boxing.world.bagHit>v',arg=stamp);p.reload();p.wait_for_timeout(1000)
 saved=c.request.get(root+f'/social/boxing/training/{pid}',headers=h).json()['total_hits'];assert saved>before,(before,saved);p.wait_for_timeout(800);assert c.request.get(root+f'/social/boxing/training/{pid}',headers=h).json()['total_hits']==saved
 assert p.evaluate("Boxing.mode==='menu'");assert not errors,errors
 print('PASS auto without a camera in tracking practice, hidden-tab stop, explicit restart, pending-hit keepalive save on reload and no background rewards')
 b.close()
