"""Read-only release verification using deployed assets and browser-local inbox fixtures."""
from pathlib import Path
from urllib.parse import urlparse
import requests,hashlib,sys
from playwright.sync_api import sync_playwright
revision=sys.argv[1];origin='https://four5-fitness-coach.onrender.com';s=requests.Session()
def get(path):
 r=s.get(origin+path,timeout=45);r.raise_for_status();return r
assert get('/status?release='+revision).json()['revision']==revision
for name in ['inbox.js','cozy-ui.js','cozy-ui.css','app.js','home.js','v19.js','themes-v29.js']:
 assert get('/static/'+name+'?release='+revision).content==Path('static',name).read_bytes(),name
assert s.get(origin+'/social/inbox',timeout=45).status_code==401
html=get('/45-fitness-coach').text
assert 'id="inboxTab"' in html and '/static/cozy-ui.js?v=1' in html
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 for width in [390,1280]:
  page=b.new_page(viewport={'width':width,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  def route(r):
   assert r.request.method=='GET',r.request.method
   assert urlparse(r.request.url).hostname==urlparse(origin).hostname
   response=s.get(r.request.url,timeout=45);r.fulfill(status=response.status_code,headers={'Content-Type':response.headers.get('Content-Type','application/octet-stream')},body=response.content)
  page.route('**/*',route);page.goto(origin+'/status');page.set_content('<button id="inboxTab">Inbox</button><button id="homeInboxTile">Inbox</button><section id="inboxPage"></section>')
  page.evaluate("""window.FitnessAccount={guest:false};window.setTab=()=>{};window.fetch=async()=>({ok:true,json:async()=>({messages:[],friends:[],unread:0,system_unread:0,settings:{enabled:false,timezone:'Asia/Bangkok',days:Array.from({length:7},(_,day)=>({day,enabled:true,time:'18:00'}))}})});""")
  page.add_style_tag(url=origin+'/static/cozy-ui.css?release='+revision);page.add_script_tag(url=origin+'/static/inbox.js?release='+revision);page.evaluate('Inbox.open()');page.wait_for_selector('.reminder-days')
  assert page.locator('.reminder-day').count()==7
  page.locator('.reminder-all input').fill('19:45');page.locator('.reminder-all button').click()
  assert all(page.locator(f'[name=time-{i}]').input_value()=='19:45' for i in range(7))
  assert page.locator('[name=enabled]').is_checked();assert not errors,errors;page.close();print(width,'PASS deployed inbox and all-days controls; GET-only network',flush=True)
 b.close()
print('VERIFIED Render',revision,flush=True)
