"""GET-only deployed-asset checks and browser-local UI fixtures."""
from pathlib import Path
from urllib.parse import urlparse
import requests,sys
from playwright.sync_api import sync_playwright
revision=sys.argv[1];origin='https://four5-fitness-coach.onrender.com';s=requests.Session()
def get(path):
 r=s.get(origin+path,timeout=35);r.raise_for_status();return r
assert get('/status?release='+revision).json()['revision']==revision
for name in ['cozy-ui.js','cozy-ui.css','themes-v29.js','themes-v29.css','theme-icons-v29.css','images/ui/category-icons.png']:
 assert get('/static/'+name+'?release='+revision).content==Path('static',name).read_bytes(),name
assert '/static/cozy-ui.js?v=2' in get('/45-fitness-coach').text
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 for width in [390,1280]:
  page=b.new_page(viewport={'width':width,'height':850});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  def route(r):
   assert r.request.method=='GET'
   assert urlparse(r.request.url).hostname==urlparse(origin).hostname
   response=s.get(r.request.url,timeout=35);r.fulfill(status=response.status_code,headers={'Content-Type':response.headers.get('Content-Type','application/octet-stream')},body=response.content)
  page.route('**/*',route);page.goto(origin+'/status');page.set_content('<body data-theme="power"><div class="lang-bar"><button>English</button></div><div class="home-hero"><h3>Coach</h3></div></body>');page.evaluate('window.setTab=()=>{}')
  for name in ['themes-v29.css','theme-icons-v29.css','cozy-ui.css']:page.add_style_tag(url=origin+'/static/'+name+'?release='+revision)
  page.add_script_tag(url=origin+'/static/cozy-ui.js?release='+revision);page.locator('.home-hero h3').click();assert page.locator('.bat-particle').count()==5;page.wait_for_timeout(1000)
  page.evaluate("document.body.dataset.theme='spicy'");page.locator('.home-hero h3').click();assert page.locator('.rabbit-particle').count()==5;page.wait_for_timeout(1000)
  page.locator('#effectsSettingsButton').click();page.locator('#clickEffectSize').fill('60');page.locator('#clickEffectsEnabled').uncheck();assert page.locator('.click-particle').count()==0;assert page.locator('#effectsSettingsButton').evaluate("n=>getComputedStyle(n,'::before').backgroundImage.includes('category-icons.png')");assert not errors,errors;page.close();print(width,'PASS deployed settings, both effects, sizing and disable; GET-only',flush=True)
 b.close()
print('VERIFIED Render',revision)
