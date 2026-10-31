"""Manual QA against a disposable localhost:5055 server; never production.
Requires Playwright, Pillow, and /usr/bin/chromium. Screenshots go to work/avatar-review.
"""
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops
from pathlib import Path
import time,io,json
out=Path('work/avatar-review');out.mkdir(parents=True,exist_ok=True)
def changed(a,b):
 a=Image.open(io.BytesIO(a)).convert('RGB');b=Image.open(io.BytesIO(b)).convert('RGB')
 diff=ImageChops.difference(a,b)
 return sum(max(p)>20 for p in diff.getdata())
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 for width in [390,1280]:
  c=browser.new_context(viewport={'width':width,'height':1000},device_scale_factor=2 if width==390 else 1,is_mobile=width==390,has_touch=width==390,reduced_motion='reduce')
  page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));root='http://127.0.0.1:5055'
  assert c.request.post(root+'/auth/register',data={'email':f'import{width}{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
  token=c.request.post(root+'/session').json()['session_token']
  r=c.request.post(root+'/profiles',headers={'X-Coach-Session':token},data={'name':'QA'+str(time.time_ns())});assert r.ok,r.text()
  page.goto(root+'/45-fitness-coach');page.wait_for_timeout(1200);page.evaluate('CharacterPage.show()')
  cv=page.locator('#characterCanvas');cv.wait_for();page.wait_for_selector('canvas[data-avatar-state=ready]')
  form=page.locator('.character-options form');assert form.locator('input[type=range]').count()==0
  for gender,h,w,clothes,hair in [('male',175,76,'sports','swept'),('female',165,60,'sports','bob'),('male',175,105,'tee','curly')]:
   for index,val in [(0,gender),(4,clothes),(5,hair)]:form.locator('select').nth(index).select_option(val)
   form.locator('input[type=number]').nth(0).fill(str(h));form.locator('input[type=number]').nth(1).fill(str(w))
   with page.expect_response(lambda r:r.url.endswith('/character') and r.request.method=='POST') as response:form.locator('button[type=submit]').click()
   saved=response.value.json();assert response.value.ok;assert saved['dimensions']['weight_kg']==w
   page.wait_for_selector('canvas[data-avatar-state=ready]');page.wait_for_timeout(300)
   cv.focus();a=cv.screenshot();page.keyboard.press('ArrowRight');b=cv.screenshot();assert changed(a,b)>200,'Rotation had no visible effect'
   # Touch pointer sequence on mobile, mouse drag on desktop.
   box=cv.bounding_box();x=box['x']+box['width']*.35;y=box['y']+box['height']*.45
   if width==390:
    session=c.new_cdp_session(page)
    session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
    session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x+100,'y':y}]})
    session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});session.detach()
   else:
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+100,y,steps=5);page.mouse.up()
   assert changed(b,cv.screenshot())>500
   page.locator('.character-rotate button').nth(1).click();cv.screenshot(path=str(out/f'{width}-{gender}-{w}-front.png'))
   # Back/side views expose clothing intersections and missing geometry.
   cv.focus()
   for _ in range(10):page.keyboard.press('ArrowRight')
   cv.screenshot(path=str(out/f'{width}-{gender}-{w}-side.png'))
   page.reload();page.wait_for_timeout(1000);page.evaluate('CharacterPage.show()');page.wait_for_selector('canvas[data-avatar-state=ready]')
   assert form.locator('select').nth(0).input_value()==gender;assert form.locator('select').nth(4).input_value()==clothes;assert form.locator('select').nth(5).input_value()==hair
   assert form.locator('input[type=number]').nth(1).input_value()==str(w)
   snap=cv.screenshot();im=Image.open(io.BytesIO(snap)).convert('RGB');assert sum(r>g*1.15 and r>b*1.15 for r,g,b in im.getdata())>1000,'Avatar invisible after reload'
  # Each face control must alter rendered pixels.
  for index,val in [(1,'round'),(2,'broad'),(3,'angular')]:
   a=cv.screenshot();form.locator('select').nth(index).select_option(val);b=cv.screenshot();assert changed(a,b)>5,('Face control had no visible effect',index)
  # Re-entering the editor after navigation must recreate a visible loaded model.
  page.evaluate("setTab('profile')");page.evaluate('CharacterPage.show()');page.wait_for_selector('canvas[data-avatar-state=ready]')
  assert not errors,errors
  print(width,'imported model, keyboard/touch rotation, facial changes, profile proportions, clothing/hair, save/reload/visibility passed',flush=True)
  c.close()
 browser.close()
