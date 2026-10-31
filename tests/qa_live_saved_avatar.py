"""Exercise the real camera-overlay module with a synthetic local camera state."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import time
root='http://127.0.0.1:5055';out=Path('work/animation-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':950});page=c.new_page();errors=[];writes=[];page.on('pageerror',lambda e:errors.append(str(e)))
  assert c.request.post(root+'/auth/register',data={'email':f'live{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
  token=c.request.post(root+'/session').json()['session_token'];r=c.request.post(root+'/profiles',headers={'X-Coach-Session':token},data={'name':'QA'+str(time.time_ns())});assert r.ok;pid=r.json()['profile']['id']
  page.goto(root+'/45-fitness-coach');page.wait_for_timeout(1000);page.evaluate('CharacterPage.show()');page.wait_for_selector('#characterCanvas[data-avatar-state=ready]');form=page.locator('.character-options form');form.locator('select').nth(4).select_option('tank');form.locator('select').nth(5).select_option('curly')
  with page.expect_response(lambda r:r.url.endswith('/character') and r.request.method=='POST') as response:form.locator('button[type=submit]').click()
  saved=response.value.json();assert response.value.ok
  # Freeze only polling state; the real overlay, fetch, renderer and retargeter run unchanged.
  page.evaluate('''id=>{setTab('workout');window.qaCamera=true;Object.defineProperty(BrowserCamera,'active',{get:()=>qaCamera});window.qaState={profile:{id},running:true,set_id:'local-qa',exercise:'curl',person_count:1,tracking:{status:['locked']},reps:0};Object.defineProperty(window,'fitnessState',{get:()=>qaState,set:()=>{},configurable:true});window.testAvatars=[];window.FitnessImportedAvatar=class extends FitnessImportedAvatar{constructor(cv){super(cv);testAvatars.push(this)}};LiveAvatar.sync()}''',pid)
  page.wait_for_selector('.live-avatar:not([hidden]) canvas[data-avatar-state=ready]')
  assert page.evaluate('testAvatars.at(-1).model.appearance')==saved['appearance'];assert page.evaluate('testAvatars.at(-1).loadedGender')==saved['appearance']['gender']
  # A complete landmark packet is solved and consumed by the actual overlay loop.
  page.evaluate('''()=>{const points=Array.from({length:33},()=>[.5,.5,1]),world=Array.from({length:33},()=>[0,0,0]);for(const [i,x,y]of [[11,.2,-.4],[12,-.2,-.4],[13,.25,-.1],[14,-.25,-.1],[15,.25,-.6],[16,-.25,-.6],[23,.1,.2],[24,-.1,.2]]){points[i]=[.5+x*.5,.5+y*.5,1];world[i]=[x,y,0]}window.qaSampleTimer=setInterval(()=>window.coachLandmarks={points,world,at:Date.now(),set_id:'local-qa',aspect:1.33,mirrored:false},50)}''')
  page.wait_for_function('LiveAvatar.pose?.valid===true');assert page.evaluate('testAvatars.at(-1).livePose.valid')
  page.locator('.live-avatar').screenshot(path=str(out/f'{width}-camera-overlay.png'))
  page.evaluate('qaState.person_count=2;LiveAvatar.sync()');assert page.locator('.live-avatar').is_hidden()
  page.evaluate('qaState.person_count=1;LiveAvatar.sync()');page.wait_for_selector('.live-avatar:not([hidden])')
  page.locator('#showLiveAvatar').uncheck();assert page.locator('.live-avatar').is_hidden();page.locator('#showLiveAvatar').check();page.wait_for_selector('.live-avatar:not([hidden])')
  page.evaluate('qaCamera=false;LiveAvatar.sync()');assert page.locator('.live-avatar').is_hidden();page.evaluate('qaCamera=true;LiveAvatar.sync()');page.wait_for_selector('.live-avatar:not([hidden])')
  page.evaluate("qaState.set_id='next-local-set';LiveAvatar.sync()");page.wait_for_function('testAvatars.length===2 && testAvatars[0].destroyed===true');page.wait_for_selector('.live-avatar canvas[data-avatar-state=ready]')
  assert page.evaluate('qaState.reps')==0,'Visual animation changed the repetition counter';assert not errors,errors
  page.evaluate('clearInterval(qaSampleTimer)');c.close();print(width,'PASS real camera overlay uses saved Quaternius, landmarks, multi-person hide, toggle, close/reopen, set cleanup; reps untouched',flush=True)
 b.close()
