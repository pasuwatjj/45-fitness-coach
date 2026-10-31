"""Read-only verification of the deployed Boxing release and assets."""
from pathlib import Path
import requests,sys
from playwright.sync_api import sync_playwright
origin=sys.argv[2] if len(sys.argv)>2 else 'https://four5-fitness-coach.onrender.com';revision=sys.argv[1];s=requests.Session()
def get(path):
 r=s.get(origin+path,timeout=40);r.raise_for_status();return r
assert get('/status?release='+revision).json()['revision']==revision
for name in ['boxing-world.js','images/boxing/arena-championship.png','inbox.js','character.js','character-renderer.js','cozy-ui.css','boxing.js','boxing-pose.js','boxing.css','profile.js','images/boxing/hud-frame.png','app.js','home.js','v19.js','images/boxing/arena.png','images/boxing/gloves.svg']:
 assert get('/static/'+name+'?release='+revision).content==Path('static',name).read_bytes(),name
assert s.get(origin+'/social/boxing',timeout=40).status_code==401
html=get('/45-fitness-coach').text;assert 'id="boxingPage"' in html and '/static/boxing.js?v=7' in html
for asset in ['boxing-world.js?v=2','boxing-pose.js?v=6','character.js?v=46','character-renderer.js?v=7','cozy-ui.css?v=4','boxing.css?v=7']:
 assert '/static/'+asset in html,asset
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']);page=b.new_page();page.set_content('<main></main>');page.add_script_tag(content=get('/static/boxing-pose.js?release='+revision).text)
 assert page.evaluate('new BoxingPose().read([],[],1000).valid') is False
 # Public-asset scene smoke: no accounts, camera, POST or production mutations.
 page.route('**/*',lambda route:route.continue_() if route.request.method=='GET' else route.abort())
 page.route(origin+'/__cage_readonly_smoke__',lambda route:route.fulfill(content_type='text/html',body='<div id="arena" style="width:900px;height:600px;position:relative"></div>'))
 page.goto(origin+'/__cage_readonly_smoke__')
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 for asset in ['vendor/three-r160.min.js','character-renderer.js','muscle-progression.js','imported-avatar.js','boxing-world.js']:
  page.add_script_tag(content=get('/static/'+asset+'?release='+revision).text)
 page.add_style_tag(content='.cage-canvas{width:900px;height:600px}')
 page.evaluate("window.I18N={lang:'en'};window.sceneSmoke=new BoxingWorld(document.getElementById('arena'));sceneSmoke.add({appearance:{},growth:{},visual:{}},0);sceneSmoke.set([{x:-1.05,z:0}],true)")
 page.wait_for_function("sceneSmoke.actors[0].canvas.dataset.avatarState==='ready'",timeout=60000)
 page.wait_for_function('sceneSmoke.renderer.info.render.calls>0')
 assert page.evaluate('sceneSmoke.bag.visible&&sceneSmoke.actors[0].spine.isBone')
 page.evaluate('sceneSmoke.set([{x:-1,z:0,bend:.9,slip:-.8,crouch:.7}],true)')
 page.wait_for_function('sceneSmoke.actors[0].spine.rotation.x>.6&&sceneSmoke.actors[0].spine.rotation.z>.2')
 page.evaluate("sceneSmoke.add({appearance:{gender:'female'},growth:{},visual:{}},1);sceneSmoke.set([{x:-.7,z:0},{x:.7,z:0}],false);sceneSmoke.view('top')")
 page.wait_for_function("sceneSmoke.actors[1].canvas.dataset.avatarState==='ready'")
 assert page.evaluate("!sceneSmoke.bag.visible&&document.querySelectorAll('#arena canvas').length===1")
 page.evaluate('sceneSmoke.destroy()');assert page.locator('#arena canvas').count()==0
 assert not errors,errors
 b.close()
print('VERIFIED exact deployed Boxing assets, template, private API, pose confidence guard and shared 3D male/female scene with bend/slip, bag removal and cleanup',revision)
