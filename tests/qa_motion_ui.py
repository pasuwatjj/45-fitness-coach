"""UI motion is real, contextual, bounded, keyboard accessible and preference aware."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];assert root.startswith('http://127.0.0.1:')
out=Path('work/motion-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);p=b.new_page(viewport={'width':1280,'height':960});errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(root+'/45-fitness-coach');p.wait_for_selector('#festivalGhost')
 p.locator('#powerTheme').click();p.locator('#festivalGhost').scroll_into_view_if_needed();p.wait_for_function("document.querySelector('.festival-scene').dataset.sceneVisible==='true'")
 a=p.locator('.festival-mascot').evaluate('e=>getComputedStyle(e).transform');p.wait_for_timeout(180);c=p.locator('.festival-mascot').evaluate('e=>getComputedStyle(e).transform');assert a!=c,(a,c)
 p.screenshot(path=str(out/'ghost-desktop.png'))
 for kind,symbol in [('health','♥'),('calendar','📅'),('leader','🏆'),('rewards','🎁'),('chat','💬'),('cardio','⚡')]:
  p.evaluate("setTab('home')");p.locator(f'.home-tile[data-feedback={kind}]').click();p.wait_for_function('k=>document.querySelectorAll(`[data-effect-kind=${k}]`).length>0',arg=kind)
  assert p.locator(f'.category-particle[data-effect-kind={kind}]').first.inner_text()==symbol
  if kind=='health':p.screenshot(path=str(out/'health-feedback.png'))
  p.wait_for_function("document.querySelectorAll('.click-particle').length===0")
 p.evaluate("setTab('home')");p.locator('#festivalGhost').focus();p.keyboard.press('Space');assert p.locator('#festivalGhost').evaluate("e=>e.classList.contains('is-waving')")
 for _ in range(12):p.locator('#festivalGhost').click()
 assert p.locator('.festival-wish').count()<=1;assert p.locator('.click-particle').count()<=20
 p.locator('#effectsSettingsButton').click();p.locator('#clickEffectsEnabled').uncheck();p.keyboard.press('Escape');assert p.locator('.festival-mascot').evaluate('e=>getComputedStyle(e).animationName')=='none';assert p.locator('.click-particle').count()==0
 p.reload();p.wait_for_selector('#festivalGhost');assert p.locator('body').get_attribute('data-effects')=='off';p.locator('#festivalGhost').click();assert p.locator('.festival-wish').count()==0
 p.locator('#effectsSettingsButton').click();p.locator('#clickEffectsEnabled').check();p.keyboard.press('Escape');p.emulate_media(reduced_motion='reduce');p.wait_for_function("document.body.dataset.effects==='off'");assert p.locator('.festival-mascot').evaluate('e=>getComputedStyle(e).animationName')=='none'
 assert not errors,errors;print('PASS real ghost motion, six contextual category feedback types, Space interaction, bounded rapid clicks, settings persistence, reduced motion and no JS errors');b.close()
