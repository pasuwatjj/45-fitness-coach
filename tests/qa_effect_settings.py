"""Local browser coverage for effects settings and single-layer semantic icons."""
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path('work/effects-review');out.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':1000});page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(__import__('os').environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5055')+'/45-fitness-coach');page.wait_for_timeout(1200)
  assert page.locator('.home-hero .effects-toggle').count()==0
  button=page.locator('#effectsSettingsButton');assert button.bounding_box()['y']>page.locator('#language-en').bounding_box()['y']
  button.click();page.wait_for_selector('#effectsSettings[open]');page.locator('#clickEffectSize').fill('64');page.wait_for_timeout(1000)
  page.locator('#effectsSettings h2').click();assert page.locator('#effectsSettings .rabbit-particle').count()==5
  assert page.locator('.click-particle').first.evaluate('n=>parseFloat(getComputedStyle(n).width)')>50
  page.wait_for_timeout(1000);assert page.locator('.click-particle').count()==0
  page.locator('#effectsSettings').screenshot(path=str(out/f'{width}-settings.png'))
  page.locator('#clickEffectsEnabled').uncheck();page.locator('#effectsSettings h2').click();assert page.locator('.click-particle').count()==0
  page.keyboard.press('Escape');assert not page.locator('#effectsSettings').is_visible();assert button.evaluate('n=>n===document.activeElement')
  page.reload();page.wait_for_timeout(800);button.click();assert not page.locator('#clickEffectsEnabled').is_checked();assert page.locator('#clickEffectSize').input_value()=='64'
  page.locator('#clickEffectsEnabled').check();page.keyboard.press('Escape');page.locator('#powerTheme').click();page.wait_for_timeout(1000)
  page.locator('.home-hero h3').click();assert page.locator('.bat-particle').count()==5;assert page.locator('.rabbit-particle').count()==0
  page.wait_for_timeout(1000);page.locator('#spicyTheme').click();page.wait_for_timeout(1000);page.locator('.home-hero h3').click();assert page.locator('.rabbit-particle').count()==5
  page.wait_for_timeout(1000)
  # Labels no longer contain the old emoji glyph; there is one CSS artwork per tile.
  assert page.locator('.home-tile-icon').evaluate_all("ns=>ns.every(n=>n.textContent===''&&getComputedStyle(n,'::before').backgroundImage.includes(n.closest('#homeBoxingTile')?'gloves.svg':'category-icons.png'))")
  assert page.locator('.home-tile').evaluate_all("ns=>ns.every(n=>['none','normal'].includes(getComputedStyle(n,'::after').content))")
  before=page.locator('.theme-sticker').count();page.evaluate('FitnessThemes.refresh();FitnessThemes.refresh()');assert before==page.locator('.theme-sticker').count()
  for theme in ['spicy','power']:
   page.locator('#'+theme+'Theme').click();page.wait_for_timeout(1000);page.locator('.home-tiles').screenshot(path=str(out/f'{width}-{theme}-icons.png'))
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
  page.emulate_media(reduced_motion='reduce');button.click();assert page.locator('#clickEffectsEnabled').is_disabled();page.locator('#effectsSettings h2').click();assert page.locator('.click-particle').count()==0
  page.keyboard.press('Escape');page.emulate_media(reduced_motion='no-preference');page.locator('.home-hero h3').click();assert page.locator('.bat-particle').count()==5
  assert not errors,errors;c.close();print(width,'PASS settings location, theme effects anywhere/dialog, size, persistence, toggle, reduced motion, keyboard/focus, icon single layers, overflow',flush=True)
 b.close()
