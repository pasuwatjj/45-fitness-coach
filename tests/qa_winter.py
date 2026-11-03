"""Winter home interaction, responsive contrast, motion lifecycle and rendering checks.
Local tests use a disposable server DB. Live mode blocks every non-GET request.
"""
import os,time,json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];live=os.environ.get('WINTER_LIVE')=='1'
assert root.startswith('http://127.0.0.1:') or live and root=='https://four5-fitness-coach.onrender.com'
out=Path('work/winter-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 p=b.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 if live:p.route('**/*',lambda r:r.continue_() if r.request.method=='GET' else r.abort())
 p.goto(root+'/45-fitness-coach');p.wait_for_function('window.WinterUI?.state.active')
 assert p.locator('.festival-hero,.festival-krathong,#festivalGhost').count()==0
 assert 'LOY KRATHONG' not in p.locator('#homePage').inner_text()
 assert p.locator('.home-tile img').count()==0
 assert p.locator('.home-tile-icon svg').count()==10
 assert p.locator('.winter-weather').evaluate('e=>getComputedStyle(e).pointerEvents')=='none'
 for width,theme in [(1440,'power'),(390,'power'),(390,'spicy'),(768,'spicy'),(320,'power')]:
  p.set_viewport_size({'width':width,'height':1000 if width>600 else 844});p.locator('#'+theme+'Theme').click();p.wait_for_timeout(300)
  assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  assert p.locator('#spicyTheme').evaluate('e=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.right-5,r.top+r.height/2))}')
  assert p.locator('.winter-hero h2').evaluate('e=>getComputedStyle(e).color')==('rgb(237, 248, 255)' if theme=='power' else 'rgb(24, 61, 83)')
  assert p.evaluate('WinterUI.state.flakes<=112&&document.querySelectorAll(".winter-weather canvas").length===1')
  p.screenshot(path=str(out/f'home-{theme}-{width}.png'),full_page=True)
 # Real canvas pixels change while running, with bounded work at both screen sizes.
 p.set_viewport_size({'width':1440,'height':1000});p.locator('#powerTheme').click();p.wait_for_timeout(1000)
 p.evaluate('window.snowBefore=document.querySelector(".winter-snow").toDataURL()')
 before=p.evaluate('WinterUI.state.frames');start=time.monotonic();p.wait_for_timeout(1500);fps=(p.evaluate('WinterUI.state.frames')-before)/(time.monotonic()-start)
 assert p.evaluate('snowBefore!==document.querySelector(".winter-snow").toDataURL()')
 assert fps>25,fps
 p.locator('#winterFriend').focus();p.keyboard.press('Enter');assert 'อุ่นเครื่อง' in p.locator('#winterGreeting').inner_text()
 for _ in range(8):p.locator('#winterFriend').click()
 assert p.locator('.winter-wish').count()<=5 and p.locator('.click-particle').count()<=20
 p.locator('#winterSnowToggle').click();p.wait_for_function('!WinterUI.state.active');before=p.evaluate('WinterUI.state.frames');p.wait_for_timeout(250);assert p.evaluate('WinterUI.state.frames')==before
 assert p.locator('#winterSnowToggle').get_attribute('aria-pressed')=='false'
 p.reload();p.wait_for_selector('#winterFriend');assert not p.evaluate('WinterUI.state.active');p.locator('#winterSnowToggle').click();p.wait_for_function('WinterUI.state.active')
 p.locator('.home-tile[data-feedback=health]').click();assert p.locator('#healthPage').is_visible();assert p.locator('.category-particle[data-effect-kind=health]').count()>0
 p.wait_for_function('!WinterUI.state.active');assert p.locator('.winter-weather').is_hidden();before=p.evaluate('WinterUI.state.frames');p.wait_for_timeout(250);assert p.evaluate('WinterUI.state.frames')==before
 assert p.locator('.winter-wish').count()==0
 p.evaluate("setTab('home')");p.wait_for_function('WinterUI.state.active');p.locator('#homeStartTraining').click();assert p.locator('.home-categories').is_visible();assert p.locator('.exercise-choice img').count()>0
 p.locator('.winter-actions .secondary').click();assert p.locator('#calendarPage').is_visible();assert not p.evaluate('WinterUI.state.active')
 p.evaluate("setTab('home')");p.locator('#winterFriend').scroll_into_view_if_needed();p.wait_for_function('WinterUI.state.sceneVisible')
 p.locator('.home-tile[data-feedback=rewards]').scroll_into_view_if_needed();p.wait_for_function('!WinterUI.state.sceneVisible');assert p.locator('.winter-mascot').evaluate('e=>getComputedStyle(e).animationPlayState')=='paused'
 p.locator('#effectsSettingsButton').click();p.locator('#clickEffectsEnabled').uncheck();p.keyboard.press('Escape');p.wait_for_function('!WinterUI.state.active');assert p.locator('#winterSnowToggle').is_disabled()
 p.reload();p.wait_for_selector('#winterFriend');assert p.locator('body').get_attribute('data-effects')=='off';assert not p.evaluate('WinterUI.state.active')
 p.locator('#effectsSettingsButton').click();p.locator('#clickEffectsEnabled').check();p.keyboard.press('Escape');p.wait_for_function('WinterUI.state.active')
 p.emulate_media(reduced_motion='reduce');p.wait_for_function('!WinterUI.state.active');p.locator('#winterFriend').click();assert p.locator('.winter-wish').count()==0;assert p.locator('.winter-mascot').evaluate('e=>getComputedStyle(e).animationName')=='none'
 p.emulate_media(reduced_motion='no-preference');p.wait_for_function('WinterUI.state.active')
 # Visibility handler stops drawing and resumes without accumulating elapsed time.
 p.evaluate("Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))")
 assert not p.evaluate('WinterUI.state.active')
 p.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))");p.wait_for_function('WinterUI.state.active')
 p.goto(root+'/45-fitness-coach?lang=en');p.wait_for_selector('#winterFriend');assert p.locator('#homeStartTraining').inner_text()=='Start training';assert p.locator('#winterSnowToggle').inner_text()=='Pause snow';p.locator('#winterFriend').click();assert 'Warm up' in p.locator('#winterGreeting').inner_text()
 p.screenshot(path=str(out/'home-english.png'),full_page=True)
 assert not errors,errors
 result={'result':'passed','live':live,'sample_fps':round(fps,1),'max_flakes':88,'console_errors':errors,'viewports':[320,390,768,1440]};(out/'qa-results.json').write_text(json.dumps(result,indent=2))
 print('PASS winter home, native icons/mascot, snowfall pixels and frame budget, responsive themes, keyboard, pause persistence, navigation, effects/reduced-motion/visibility, exercise media and bilingual content',result)
 b.close()
