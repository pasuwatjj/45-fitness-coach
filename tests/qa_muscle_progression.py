"""Local-only browser integration. Uses a disposable DB; no test HTTP endpoints.
Run with the local app using FITNESS_DATA_PATH=$PWD/work/progression-qa.db.
"""
import sys,time,io,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from leaderboard import LeaderboardStore
import rewards,character
from playwright.sync_api import sync_playwright
from PIL import Image,ImageChops
root='http://127.0.0.1:5055';store=LeaderboardStore(Path('work/progression-qa.db'))
out=Path('work/progression-review');out.mkdir(parents=True,exist_ok=True)
def changed(a,b):
 im=ImageChops.difference(Image.open(io.BytesIO(a)).convert('RGB'),Image.open(io.BytesIO(b)).convert('RGB'))
 return sum(max(p)>15 for p in im.getdata())
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':1000},device_scale_factor=2 if width==390 else 1,is_mobile=width==390,has_touch=width==390,reduced_motion='reduce');page=c.new_page();errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' and 'THREE.WebGLProgram' in m.text else None)
  assert c.request.post(root+'/auth/register',data={'email':f'growth{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
  token=c.request.post(root+'/session').json()['session_token'];r=c.request.post(root+'/profiles',headers={'X-Coach-Session':token},data={'name':'RPG'+str(time.time_ns())});assert r.ok,r.text();pid=r.json()['profile']['id']
  page.goto(root+'/45-fitness-coach');page.wait_for_timeout(900);page.evaluate('CharacterPage.show()');page.wait_for_selector('canvas[data-avatar-state=ready]')
  cv=page.locator('#characterCanvas');form=page.locator('.character-options form')
  form.locator('input[type=number]').nth(0).fill('175');form.locator('input[type=number]').nth(1).fill('76')
  with page.expect_response(lambda r:r.url.endswith('/character') and r.request.method=='POST'):form.locator('button[type=submit]').click()
  page.locator('.character-rotate button').nth(1).click();before=cv.screenshot(path=str(out/f'{width}-beginner.png'))
  model=c.request.get(root+f'/profiles/{pid}/character',headers={'X-Coach-Session':token}).json();assert all(v['level']==1 for v in model['growth']['parts'].values())
  # A completed but not verified set must not change EXP, pixels or user history.
  sid='pending-'+str(pid);store.save_set(sid,pid,'curl','right',20,0,0,20,{},difficulty='expert')
  page.evaluate("window.dispatchEvent(new Event('fitness-workout-saved'))");page.wait_for_timeout(300);assert c.request.get(root+f'/profiles/{pid}/character',headers={'X-Coach-Session':token}).json()['growth']['parts']['arms']['total_exp']==0
  assert changed(before,cv.screenshot())<10
  # Save verification using the same authoritative writer used after /pause.
  # Keep an unsaved hairstyle edit while progress refreshes.
  form.locator('select').nth(5).select_option('swept');pre_growth=cv.screenshot()
  rewards.save_quality(store,sid,pid,'curl','right',20,5,3,accepted=20)
  page.evaluate("window.dispatchEvent(new Event('fitness-workout-saved'))");page.wait_for_function("document.querySelector('[data-part=arms]').textContent.includes('LV 5')")
  assert form.locator('select').nth(5).input_value()=='swept'
  arm=cv.screenshot(path=str(out/f'{width}-right-arm.png'));assert changed(pre_growth,arm)>300
  model=c.request.get(root+f'/profiles/{pid}/character',headers={'X-Coach-Session':token}).json();assert model['growth']['arm_parts']['left']['level']==1;assert model['growth']['arm_parts']['right']['level']==5
  for group in ['chest','back','legs','shoulders']:
   exercise=next(k for k,v in character.CATALOG.items() if v['group']==group);sid=group+'-'+str(pid)
   store.save_set(sid,pid,exercise,'both',20,0,20,20,{},difficulty='expert');rewards.save_quality(store,sid,pid,exercise,'both',20,0,0,accepted=40)
   page.evaluate("window.dispatchEvent(new Event('fitness-workout-saved'))");page.wait_for_function(f"document.querySelector('[data-part={group}]').textContent.includes('LV 5')")
  sid='left-'+str(pid);store.save_set(sid,pid,'curl','left',20,0,20,0,{},difficulty='expert');rewards.save_quality(store,sid,pid,'curl','left',20,0,0,accepted=20)
  page.evaluate("window.dispatchEvent(new Event('fitness-workout-saved'))");page.wait_for_timeout(300)
  after=cv.screenshot(path=str(out/f'{width}-developed.png'));assert changed(before,after)>1000
  with page.expect_response(lambda r:r.url.endswith('/character') and r.request.method=='POST'):form.locator('button[type=submit]').click()
  page.reload();page.wait_for_timeout(900);page.evaluate('CharacterPage.show()');page.wait_for_selector('canvas[data-avatar-state=ready]')
  assert form.locator('select').nth(5).input_value()=='swept';assert form.locator('input[type=number]').nth(1).input_value()=='76'
  assert c.request.get(root+f'/profiles/{pid}/character',headers={'X-Coach-Session':token}).json()['growth']==character.growth(store,pid)
  assert form.locator('input[type=range]').count()==0
  for gender in ['male','female']:
   form.locator('select').nth(0).select_option(gender);page.wait_for_selector('canvas[data-avatar-state=ready]')
   for clothing in ['sports','tank','tee']:
    form.locator('select').nth(4).select_option(clothing);cv.screenshot(path=str(out/f'{width}-{gender}-{clothing}.png'))
  assert not errors,errors;c.close();print(width,'PASS verified EXP refresh, zero unverified credit, independent arms/groups, unsaved cosmetics, save/reload, all clothing/genders',flush=True)
 b.close()
