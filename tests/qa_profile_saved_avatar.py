"""Disposable localhost profile/editor parity check; never production accounts."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import time,json
out=Path('work/profile-avatar-review');out.mkdir(parents=True,exist_ok=True)
root='http://127.0.0.1:5055'
fingerprint="""()=>{const r=window.testAvatars.at(-1);return {model:{appearance:r.model.appearance,visual:r.model.visual,growth:r.model.growth},meshes:r.body.children.map(m=>({name:m.name,color:m.material?.color?.getHexString(),vertices:Array.from(m.geometry?.attributes.position.array||[])}))}}"""
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':1000},device_scale_factor=2 if width==390 else 1,reduced_motion='reduce');page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  assert c.request.post(root+'/auth/register',data={'email':f'profile{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
  token=c.request.post(root+'/session').json()['session_token'];r=c.request.post(root+'/profiles',headers={'X-Coach-Session':token},data={'name':'QA'+str(time.time_ns())});assert r.ok,r.text();pid=r.json()['profile']['id']
  def instrument():
   page.evaluate("()=>{window.testAvatars=[];window.FitnessImportedAvatar=class extends FitnessImportedAvatar{constructor(canvas){super(canvas);window.testAvatars.push(this)}}}")
  def profile():
   page.evaluate("setTab('profile')");page.wait_for_selector('.profile-character-preview',state='attached');page.locator('.profile-character-preview').evaluate('e=>e.parentElement.open=true');page.wait_for_selector('.profile-character-preview canvas[data-avatar-state=ready]')
  page.goto(root+'/45-fitness-coach');page.wait_for_timeout(900);instrument()
  for gender,hair,clothes in [('male','swept','tank'),('female','bob','tee')]:
   page.evaluate('CharacterPage.show()');page.wait_for_selector('#characterCanvas[data-avatar-state=ready]');form=page.locator('.character-options form')
   for i,value in [(0,gender),(1,'round'),(2,'broad'),(3,'angular'),(4,clothes),(5,hair)]:form.locator('select').nth(i).select_option(value)
   for i,value in enumerate(['#337755','#633c88','#231a16','#c78f68','#172d4c']):form.locator('input[type=color]').nth(i).fill(value)
   form.locator('input[type=number]').nth(0).fill('178');form.locator('input[type=number]').nth(1).fill('72')
   with page.expect_response(lambda r:r.url.endswith('/character') and r.request.method=='POST') as saved:form.locator('button[type=submit]').click()
   assert saved.value.ok;page.wait_for_selector('#characterCanvas[data-avatar-state=ready]');editor=page.evaluate(fingerprint)
   profile();assert page.evaluate(fingerprint)==editor,'Profile differs from saved editor geometry/material/model'
   assert page.evaluate('testAvatars.at(-2).destroyed===true'),'Previous renderer leaked'
   cv=page.locator('.profile-character-preview canvas');cv.focus();before=page.evaluate('testAvatars.at(-1).yaw');page.keyboard.press('ArrowRight');assert page.evaluate('testAvatars.at(-1).yaw')>before
   cv.screenshot(path=str(out/f'{width}-{gender}.png'))
   page.reload();page.wait_for_timeout(900);instrument();profile();assert page.evaluate(fingerprint)==editor,'Reload lost saved appearance'
  # Both owner and shared member previews use the same renderer and authoritative model.
  assert c.request.post(root+f'/social/sharing/{pid}',headers={'X-Coach-Session':token},data={'enabled':True}).ok
  page.evaluate('(id)=>ProfileDashboard.openMember(id)',pid);page.wait_for_selector('.profile-character-preview',state='attached');page.locator('.profile-character-preview').evaluate('e=>e.parentElement.open=true');page.wait_for_selector('.profile-character-preview canvas[data-avatar-state=ready]')
  assert page.evaluate(fingerprint)==editor
  assert page.locator('#profilePage input[type=file]').count()==0,'Shared preview must stay read-only'
  # Close/reopen the disclosure and leave/re-enter the page.
  box=page.locator('.profile-character-preview');box.evaluate('e=>e.parentElement.open=false');box.evaluate('e=>e.parentElement.open=true');profile();assert page.evaluate(fingerprint)==editor
  assert not errors,errors;c.close();print(width,'PASS profile/editor exact model+mesh+material parity, saved changes, reload, rotation, shared read-only preview, disposal/re-entry',flush=True)
 b.close()
