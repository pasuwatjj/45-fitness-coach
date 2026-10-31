"""Read-only verification of the deployed Boxing release and assets."""
from pathlib import Path
import requests,sys
from playwright.sync_api import sync_playwright
origin='https://four5-fitness-coach.onrender.com';revision=sys.argv[1];s=requests.Session()
def get(path):
 r=s.get(origin+path,timeout=40);r.raise_for_status();return r
assert get('/status?release='+revision).json()['revision']==revision
for name in ['boxing.js','boxing-pose.js','boxing.css','profile.js','images/boxing/hud-frame.png','app.js','home.js','v19.js','images/boxing/arena.png','images/boxing/gloves.svg']:
 assert get('/static/'+name+'?release='+revision).content==Path('static',name).read_bytes(),name
assert s.get(origin+'/social/boxing',timeout=40).status_code==401
html=get('/45-fitness-coach').text;assert 'id="boxingPage"' in html and '/static/boxing.js?v=2' in html
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=b.new_page();page.set_content('<main></main>');page.add_script_tag(content=get('/static/boxing-pose.js?release='+revision).text)
 assert page.evaluate('new BoxingPose().read([],[],1000).valid') is False
 b.close()
print('VERIFIED exact deployed Boxing assets, template entry point, private API and pose confidence guard',revision)
