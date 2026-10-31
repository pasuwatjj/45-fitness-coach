# Run manually against a disposable local server on port 5055. Requires Playwright and Chromium.
# Writes screenshots to /tmp/avatar-qa; never use with production data.
from playwright.sync_api import sync_playwright
import time
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':900});page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  root='http://127.0.0.1:5055';r=c.request.post(root+'/auth/register',data={'email':f'qa{width}{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'});assert r.ok
  token=c.request.post(root+'/session').json()['session_token']
  assert c.request.post(root+'/profiles',headers={'X-Coach-Session':token},data={'name':'QA '+str(time.time_ns())}).ok
  page.goto(root+'/45-fitness-coach');page.wait_for_timeout(1500);page.evaluate('CharacterPage.show()');cv=page.locator('#characterCanvas');cv.wait_for();page.wait_for_timeout(1000)
  form=page.locator('.character-options form');assert form.locator('input[type=range]').count()==0
  assert cv.get_attribute('data-renderer')=='webgl'
  for h,w in [(175,58),(175,105),(195,95)]:
   form.locator('input[type=number]').nth(0).fill(str(h));form.locator('input[type=number]').nth(1).fill(str(w))
   form.locator('select').nth(1).select_option('round');form.locator('select').nth(2).select_option('broad');form.locator('select').nth(4).select_option('tee')
   with page.expect_response(lambda r:r.url.endswith('/character') and r.request.method=='POST') as saved:form.locator('button[type=submit]').click()
   assert saved.value.ok
   cv.focus();page.keyboard.press('ArrowRight');page.wait_for_timeout(200)
  cv.screenshot(path=f'/tmp/avatar-qa/{width}.png')
  page.reload();page.wait_for_timeout(1000);page.evaluate('CharacterPage.show()');cv.wait_for();assert form.locator('select').nth(4).input_value()=='tee';assert form.locator('input[type=number]').nth(1).input_value()=='95';assert not errors,errors
  print(width,'WebGL, no manual body controls, profile changes, face/clothing/save/reload passed');c.close()
 b.close()
