"""Read-only verification of the deployed Boxing release and assets."""
from pathlib import Path
import requests,sys
from playwright.sync_api import sync_playwright
origin=sys.argv[2] if len(sys.argv)>2 else 'https://four5-fitness-coach.onrender.com';revision=sys.argv[1];s=requests.Session()
def get(path):
 r=s.get(origin+path,timeout=40);r.raise_for_status();return r
assert get('/status?release='+revision).json()['revision']==revision
assert 'boxing-mode-cards' in get('/static/boxing.js?release='+revision).text
for name in ['boxing-world.js','images/boxing/champion-belt.svg','images/boxing/mode-menu.png','images/boxing/arena-championship.png','inbox.js','character.js','character-renderer.js','cozy-ui.css','boxing.js','boxing-pose.js','boxing.css','profile.js','images/boxing/hud-frame.png','app.js','home.js','v19.js','images/boxing/arena.png','images/boxing/gloves.svg']:
 assert get('/static/'+name+'?release='+revision).content==Path('static',name).read_bytes(),name
assert s.get(origin+'/social/boxing',timeout=40).status_code==401
assert s.get(origin+'/social/boxing/belts/1',timeout=40).status_code==401
html=get('/45-fitness-coach').text;assert 'id="boxingPage"' in html and '/static/boxing.js?v=12' in html
for asset in ['profile.js?v=50','boxing-world.js?v=6','boxing-pose.js?v=9','character.js?v=46','character-renderer.js?v=7','cozy-ui.css?v=4','boxing.css?v=9']:
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
 assert page.evaluate("sceneSmoke.bag.visible&&sceneSmoke.actors[0].spine.isBone&&sceneSmoke.mode==='follow'&&sceneSmoke.distance<3.5")
 assert page.evaluate("BoxingContact.sweep(new THREE.Vector3(0,1,-1),new THREE.Vector3(0,1,1),{a:new THREE.Vector3(0,.7,0),b:new THREE.Vector3(0,1.3,0),radius:.3},.095).z<-.39")
 page.evaluate("sceneSmoke.set([{x:-1,z:0,bend:-.8,posture:{turn:.7,hipTurn:.1,headPitch:-.3}}],true)")
 page.wait_for_function('sceneSmoke.actors[0].chest.rotation.x<-.2&&sceneSmoke.actors[0].chest.rotation.y>.35&&sceneSmoke.actors[0].neck.rotation.x<-.2')
 assert page.evaluate("sceneSmoke.hallWalls.length===8&&['left','right'].every(s=>sceneSmoke.actors[0].bones[s+'Arm'].glove?.getObjectByName('wrist-cuff'))")
 page.evaluate('sceneSmoke.set([{x:-1,z:0,bend:.9,slip:-.8,crouch:.7}],true)')
 page.wait_for_function('sceneSmoke.actors[0].spine.rotation.x+sceneSmoke.actors[0].chest.rotation.x>.7&&sceneSmoke.actors[0].spine.rotation.z+sceneSmoke.actors[0].chest.rotation.z>.2')
 page.evaluate("sceneSmoke.add({appearance:{gender:'female'},growth:{},visual:{}},1);sceneSmoke.set([{x:-.7,z:0},{x:.7,z:0}],false);sceneSmoke.view('top')")
 page.wait_for_function("sceneSmoke.actors[1].canvas.dataset.avatarState==='ready'")
 assert page.evaluate("!sceneSmoke.bag.visible&&document.querySelectorAll('#arena canvas').length===1")
 page.evaluate("sceneSmoke.set([{x:-.7,z:0,presentation:'down',presentationAt:performance.now()-1500,recoverAfter:10},{x:.7,z:0,presentation:'waiting'}],false)")
 page.wait_for_function("sceneSmoke.actors[0].downAmount>.9&&sceneSmoke.actors[0].canvas.dataset.presentation==='lying'&&sceneSmoke.actors[0].body.rotation.x < -1.4")
 page.evaluate("sceneSmoke.set([{x:-.7,z:0,presentation:'champion',presentationAt:performance.now()-2000},{x:.7,z:0,presentation:'down',presentationAt:performance.now()-2000,recoverAfter:null}],false)")
 page.wait_for_function('sceneSmoke.actors[0].belt?.visible&&sceneSmoke.actors[0].belt.children.some(m=>m.material?.map?.image?.complete)&&sceneSmoke.actors[1].downAmount>.9')
 page.evaluate('sceneSmoke.destroy()');assert page.locator('#arena canvas').count()==0
 assert not errors,errors
 # Render the deployed menu without accessing private APIs or requesting a camera.
 page.set_content('<select id="profile"><option value="1">Preview</option></select><section id="boxingPage"></section>')
 page.evaluate("window.I18N={lang:'th'};window.FitnessAccount={guest:true}")
 page.add_style_tag(content=get('/static/boxing.css?release='+revision).text)
 page.add_script_tag(content=get('/static/boxing-pose.js?release='+revision).text)
 page.add_script_tag(content=get('/static/boxing.js?release='+revision).text)
 page.evaluate('Boxing.open()')
 assert page.locator('.boxing-menu').is_visible()
 assert page.locator('.boxing-mode-card').count()==2
 assert page.locator('.boxing-arena').is_hidden()
 assert page.evaluate('Boxing.world===null&&document.querySelector(".boxing-preview video").srcObject===null')
 assert not errors,errors
 b.close()
print('VERIFIED exact deployed Boxing assets, template, private API, pose confidence guard and shared 3D male/female scene with tracked upper-body/head rotation, MMA gloves, decorated hall, bend/slip, swept contact, close camera, lying knockdown, 45 champion belt, bag removal and cleanup',revision)
