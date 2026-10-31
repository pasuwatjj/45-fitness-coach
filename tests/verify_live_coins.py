"""Read-only deployment check: exact code/artwork and real production PNG rendering."""
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
import requests,hashlib,sys
revision=sys.argv[1];origin='https://four5-fitness-coach.onrender.com';s=requests.Session();out=Path('work/live-coins');out.mkdir(parents=True,exist_ok=True)
def get(path):
 r=s.get(origin+path,timeout=45);r.raise_for_status();return r
assert get('/status?release='+revision).json()['revision']==revision
for name in ['coin-art.js','coin-art.css','play-coach.js','rewards.js','cardio.js','profile.js','community.js','challenges.js','images/coins/fitness-coins.png']:
 assert hashlib.sha256(get('/static/'+name+'?release='+revision).content).hexdigest()==hashlib.sha256(Path('static',name).read_bytes()).hexdigest(),name
html=get('/45-fitness-coach').text;assert '/static/coin-art.js?v=2' in html and '/static/coin-art.css?v=2' in html
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':700});page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  def route(r):
   if r.request.method!='GET' or urlparse(r.request.url).hostname!=urlparse(origin).hostname:r.abort();return
   response=s.get(r.request.url,timeout=45);r.fulfill(status=response.status_code,headers={'Content-Type':response.headers.get('Content-Type','application/octet-stream')},body=response.content)
  page.route('**/*',route);page.goto(origin+'/status');page.set_content('<main class="training-wallet" style="display:flex;flex-wrap:wrap;gap:24px;padding:30px;background:#30253d"></main>');page.add_style_tag(url=origin+'/static/coin-art.css?release='+revision);page.add_script_tag(url=origin+'/static/coin-art.js?release='+revision)
  page.evaluate("for(const key of ['beginner','pro','expert','universal'])document.querySelector('main').append(CoinArt.create(key))")
  page.wait_for_function("document.querySelectorAll('[data-artwork=ready]').length===4");assert len(set(hashlib.sha256(page.locator('.coin-art').nth(i).screenshot()).hexdigest() for i in range(4)))==4
  page.locator('main').screenshot(path=str(out/f'{width}-coins.png'));assert not errors,errors;c.close();print(width,'PASS exact deployed artwork, transparent badges, four distinct currency icons; GET-only',flush=True)
 b.close()
print('VERIFIED Render',revision,flush=True)
