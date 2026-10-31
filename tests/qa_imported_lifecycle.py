"""Imported avatar lifecycle and alternate studio QA; localhost disposable data only."""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time
out=Path('work/avatar-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce');page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  root='http://127.0.0.1:5055';assert c.request.post(root+'/auth/register',data={'email':f'life{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
  token=c.request.post(root+'/session').json()['session_token'];assert c.request.post(root+'/profiles',headers={'X-Coach-Session':token},data={'name':'QA'+str(time.time_ns())}).ok
  page.goto(root+'/45-fitness-coach');page.wait_for_timeout(1000);page.evaluate('CharacterPage.show()');page.wait_for_selector('canvas[data-avatar-state=ready]')
  page.evaluate('CharacterPage.leave()');page.add_style_tag(url=root+'/static/avatar-studio.css');page.add_script_tag(url=root+'/static/avatar-studio.js');page.evaluate('CharacterPage.open()');page.wait_for_selector('canvas[data-avatar-state=ready]')
  form=page.locator('.studio-form');form.locator('[name=height_cm]').fill('175');form.locator('[name=weight_kg]').fill('76');form.locator('[name=clothing]').select_option('tank');form.locator('[name=hair]').select_option('ponytail');form.locator('[name=top_color]').fill('#496455');form.locator('[name=eye_color]').fill('#2e6d64');form.locator('[name=hair_color]').fill('#221a15')
  with page.expect_response(lambda r:r.url.endswith('/character') and r.request.method=='POST') as r:form.locator('button[type=submit]').click()
  assert r.value.ok;assert r.value.json()['appearance']['clothing']=='tank';assert r.value.json()['appearance']['eye_color']=='#2e6d64'
  # Editing again after a successful save must update the current model immediately.
  before=page.locator('.studio-stage canvas').screenshot();form.locator('[name=top_color]').fill('#882233');after=page.locator('.studio-stage canvas').screenshot();assert before!=after
  form.locator('[name=top_color]').fill('#496455')
  page.evaluate('CharacterPage.leave();CharacterPage.open()');page.wait_for_selector('canvas[data-avatar-state=ready]');assert form.locator('[name=clothing]').input_value()=='tank';assert form.locator('[name=hair]').input_value()=='ponytail'
  page.locator('.studio-view button').nth(2).click();page.locator('.studio-stage canvas').screenshot(path=str(out/f'{width}-tank-back.png'))
  page.locator('.studio-view button').nth(0).click();page.locator('#characterPage').screenshot(path=str(out/f'{width}-studio.png'))
  # Cold-load gender race must render the most recently selected model.
  page.evaluate('''async()=>{FitnessImportedAvatar.cache.clear();const model=await (await fetch('/profiles/'+document.getElementById('profile').value+'/character')).json();const cv=document.createElement('canvas');cv.width=400;cv.height=500;document.body.append(cv);window.qaRenderer=new FitnessImportedAvatar(cv);qaRenderer.set({...model,appearance:{...model.appearance,gender:'male'}});qaRenderer.set({...model,appearance:{...model.appearance,gender:'female'}})}''')
  page.wait_for_function("qaRenderer.loadedGender==='female'");page.evaluate('qaRenderer.destroy();qaRenderer.canvas.remove()')
  # Teardown while requests are still pending must not resurrect rendering.
  page.evaluate('''async()=>{FitnessImportedAvatar.cache.clear();const model=await (await fetch('/profiles/'+document.getElementById('profile').value+'/character')).json();const cv=document.createElement('canvas');document.body.append(cv);window.qaDestroyed=new FitnessImportedAvatar(cv);qaDestroyed.set(model);qaDestroyed.destroy();cv.remove()}''')
  page.wait_for_timeout(500);assert page.evaluate('qaDestroyed.destroyed && qaDestroyed.frame===null && qaDestroyed.root.children.length===0')
  assert not errors,errors;c.close();print(width,'studio save/load, back view, cold-load gender race, pending-load teardown passed',flush=True)
 c=b.new_context();page=c.new_page();page.route('**/models/quaternius/male.json',lambda route:route.abort());page.goto(root+'/45-fitness-coach')
 page.evaluate('''()=>{const cv=document.createElement('canvas');cv.width=400;cv.height=500;document.body.append(cv);window.qaFallback=new FitnessImportedAvatar(cv);qaFallback.set({appearance:{gender:'male'},visual:{height_scale:1,fullness:.2}})}''')
 page.wait_for_selector('canvas[data-avatar-state=error]');assert page.evaluate('qaFallback.body.children.length>0 && qaFallback.root.children.length>0');page.evaluate('qaFallback.destroy()');c.close();print('Asset failure retains visible fallback',flush=True)
 b.close()
