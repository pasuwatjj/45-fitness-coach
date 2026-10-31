"""Verify artwork mapping/accessibility; original asset review is a separate release gate."""
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page()
 page.route('https://coin-test.invalid/**',lambda r:r.fulfill(status=200,content_type='text/html',body='<main></main>') if r.request.resource_type=='document' else r.abort())
 page.goto('https://coin-test.invalid/');page.add_script_tag(content=(root/'static/coin-art.js').read_text());page.add_style_tag(content=(root/'static/coin-art.css').read_text())
 for key,name in [('beginner','yellow-muscle.png'),('pro','purple-muscle.png'),('expert','expert-muscle.png'),('universal','blue-universal.png')]:
  page.evaluate('(key)=>document.querySelector("main").replaceChildren(CoinArt.create(key))',key)
  icon=page.locator('.coin-art');assert icon.get_attribute('data-currency')==key;assert icon.locator('img').get_attribute('src')=='/static/images/coins/'+name
  assert icon.get_attribute('aria-label');page.wait_for_selector('[data-artwork=unavailable]');assert icon.locator('img').is_hidden();assert icon.locator('.coin-art-fallback').is_visible()
 page.evaluate('CoinArt.text(document.querySelector("main"),"1000 🟡 → 1 🌐")');assert page.locator('.coin-art').count()==2;assert page.locator('main').inner_text().startswith('1000')
 print('PASS four currency mappings, exchange text, accessible labels, safe missing-file fallback. Original artwork files still required.');b.close()
