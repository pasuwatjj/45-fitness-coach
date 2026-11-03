"""Local bag practice: punch budget, guarded recovery, resume and visible effects."""
import os,time
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];assert root.startswith('http://127.0.0.1:')
out=Path('work/boxing-charge-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 c=b.new_context(viewport={'width':1200,'height':950})
 assert c.request.post(root+'/auth/register',data={'email':f'energy{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']}
 pid=c.request.post(root+'/profiles',headers=h,data={'name':'Stamina '+str(time.time_ns())[-6:]}).json()['profile']['id']
 assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{}}).ok
 p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 p.goto(root+'/45-fitness-coach?lang=en');p.locator('#homeBoxingTile').click();p.wait_for_function("!document.querySelector('[data-mode=practice]').disabled")
 p.locator('[data-mode=practice]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-primary').click();p.wait_for_function('Boxing.world?.actors[0]?.body',timeout=60000)
 p.wait_for_function("!document.querySelector('.boxing-training button').disabled")
 p.evaluate("window.nativeRender=Boxing.world.renderer.render.bind(Boxing.world.renderer);let frameAt=0;Boxing.world.renderer.render=(...args)=>{if(performance.now()-frameAt>100){frameAt=performance.now();nativeRender(...args)}};window.energy=()=>document.querySelector('.stamina-bar progress').value;window.lowEnergy=20;window.effectsSeen=false;const hit=Boxing.world.hitEffect.bind(Boxing.world);Boxing.world.hitEffect=(...a)=>{effectsSeen=true;hit(...a)};window.energyTimer=setInterval(()=>lowEnergy=Math.min(lowEnergy,energy()),20);window.punchTimer=setInterval(()=>{document.body.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyE',bubbles:true}));setTimeout(()=>document.body.dispatchEvent(new KeyboardEvent('keyup',{code:'KeyE',bubbles:true})),25)},540);void 0")

 try:p.wait_for_function('lowEnergy<2',timeout=16000)
 except Exception:
  print(p.evaluate('({lowEnergy,energy:energy(),effectsSeen,status:document.querySelector(\".boxing-training\").innerText})'));raise
 p.evaluate('clearInterval(punchTimer)')
 assert p.evaluate('effectsSeen')
 p.keyboard.down('f');p.wait_for_function('energy()>=10',timeout=3000);p.keyboard.up('f');p.wait_for_function('energy()>=19.5',timeout=3000)
 # Exercise the actual effect renderer and freeze one native 3D impact frame for review.
 p.evaluate("Boxing.world.hitEffect({result:'hit',charge_multiplier:2},{x:0,z:0});Boxing.world.running=false;cancelAnimationFrame(Boxing.world.frame);const fx=Boxing.world.hitEffects.at(-1);fx.particles(.22);nativeRender(Boxing.world.scene,Boxing.world.camera);void 0")
 p.locator('.boxing-arena').screenshot(path=str(out/'impact-practice.png'))
 p.evaluate('clearInterval(energyTimer)');p.locator('.boxing-back').click();p.wait_for_function("Boxing.mode==='menu'")
 p.locator('[data-mode=practice]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-primary').click();p.wait_for_function('Boxing.world?.actors[0]?.body')
 assert p.locator('.stamina-bar progress').evaluate('(e)=>e.value')==20
 p.locator('.boxing-back').click();assert not errors,errors
 print('PASS practice open/reopen, punch spam exhausts stamina, guard/rest recover at configured rate, native impacts and no browser errors')
 b.close()
