"""UI motion is real, contextual, bounded, keyboard accessible and preference aware."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];assert root.startswith('http://127.0.0.1:')
out=Path('work/motion-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);p=b.new_page(viewport={'width':1280,'height':960});errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(root+'/45-fitness-coach');p.wait_for_selector('#winterFriend')
 p.locator('#powerTheme').click();p.locator('#winterFriend').scroll_into_view_if_needed();p.wait_for_function("WinterUI.state.sceneVisible")
 a=p.locator('.winter-mascot').evaluate('e=>getComputedStyle(e).transform');p.wait_for_timeout(180);c=p.locator('.winter-mascot').evaluate('e=>getComputedStyle(e).transform');assert a!=c,(a,c)
 p.screenshot(path=str(out/'snowman-desktop.png'))
 for kind,symbol in [('health','♥'),('calendar','📅'),('leader','🏆'),('rewards','🎁'),('chat','💬'),('cardio','⚡')]:
  p.evaluate("setTab('home')");p.locator(f'.home-tile[data-feedback={kind}]').click();p.wait_for_function('k=>document.querySelectorAll(`[data-effect-kind=${k}]`).length>0',arg=kind)
  assert p.locator(f'.category-particle[data-effect-kind={kind}]').first.inner_text()==symbol
  if kind=='health':p.screenshot(path=str(out/'health-feedback.png'))
  p.wait_for_function("document.querySelectorAll('.click-particle').length===0")
 p.evaluate("setTab('home')");p.locator('#winterFriend').focus();p.keyboard.press('Space');assert p.locator('#winterFriend').evaluate("e=>e.classList.contains('is-waving')")
 for _ in range(12):p.locator('#winterFriend').click()
 assert p.locator('.winter-wish').count()<=5;assert p.locator('.click-particle').count()<=20
 p.locator('#effectsSettingsButton').click();p.locator('#clickEffectsEnabled').uncheck();p.keyboard.press('Escape');assert p.locator('.winter-mascot').evaluate('e=>getComputedStyle(e).animationName')=='none';assert p.locator('.click-particle').count()==0
 p.reload();p.wait_for_selector('#winterFriend');assert p.locator('body').get_attribute('data-effects')=='off';p.locator('#winterFriend').click();assert p.locator('.winter-wish').count()==0
 p.locator('#effectsSettingsButton').click();p.locator('#clickEffectsEnabled').check();p.keyboard.press('Escape');p.emulate_media(reduced_motion='reduce');p.wait_for_function("document.body.dataset.effects==='off'");assert p.locator('.winter-mascot').evaluate('e=>getComputedStyle(e).animationName')=='none'
 assert not errors,errors;print('PASS real snowman motion, six contextual category feedback types, Space interaction, bounded rapid clicks, settings persistence, reduced motion and no JS errors');b.close()
