"""Read-only deterministic framing/impact fixture for the final-hit renderer."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];assert root.startswith('http://127.0.0.1:')
out=Path('work/boxing-finale-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']);p=b.new_page(viewport={'width':1100,'height':700});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 p.route(root+'/__finale_scene__',lambda r:r.fulfill(content_type='text/html',body='<link rel="stylesheet" href="/static/boxing.css"><style>body{margin:0}.boxing-arena{height:650px!important;min-height:0!important;width:100%;border:0}.boxing-fighters{height:100%}</style><div class="boxing-arena"><div class="boxing-fighters"></div></div>'))
 p.goto(root+'/__finale_scene__')
 for name in ['vendor/three-r160.min.js','character-renderer.js','muscle-progression.js','imported-avatar.js','boxing-motion.js','boxing-finale.js','boxing-world.js']:p.add_script_tag(url=root+'/static/'+name)
 p.evaluate("window.I18N={lang:'en'};window.scene=new BoxingWorld(document.querySelector('.boxing-fighters'));scene.add({appearance:{},growth:{},visual:{}},0);scene.add({appearance:{hair_color:'#e5e5e5'},growth:{},visual:{}},1);scene.set([{x:-.48,z:0,controlMode:'computer'},{x:.48,z:0,controlMode:'computer'}],false);window.sceneWall=1000000;scene.serverNow=()=>sceneWall")
 p.wait_for_function("scene.actors.every(a=>a.body&&a.canvas.dataset.avatarState==='ready')",timeout=60000)
 p.evaluate("scene.finale.set({id:'frame',winner:1,target:2,hand:'right',punch_type:'straight',started_at:1000,duration:6,players:[{uid:1,x:-.48,z:0},{uid:2,x:.48,z:0}]});sceneWall=1001950")
 p.wait_for_function('scene.finale.effect?.visible');p.wait_for_timeout(900)
 distance=p.evaluate("scene.actors[0].bones.rightArm.lower.localToWorld(scene.actors[0].bones.rightArm.contactEnd.clone()).distanceTo(scene.actors[1].neck.localToWorld(new THREE.Vector3(0,.22,0)))")
 assert distance<.25,distance
 p.locator('.boxing-arena').screenshot(path=str(out/'impact-desktop.png'))
 for width,label in [(1100,'desktop'),(390,'mobile')]:
  p.set_viewport_size({'width':width,'height':700});p.evaluate('sceneWall=1005500');p.wait_for_timeout(1200)
  bounds=p.evaluate("scene.actors.flatMap(a=>[a.neck.localToWorld(new THREE.Vector3(0,.22,0)),a.bones.leftLeg.foot.getWorldPosition(new THREE.Vector3()),a.bones.rightLeg.foot.getWorldPosition(new THREE.Vector3())]).map(v=>{v.project(scene.camera);return [v.x,v.y]})")
  assert all(abs(x)<.98 and abs(y)<.95 for x,y in bounds),(label,bounds)
  p.locator('.boxing-arena').screenshot(path=str(out/('settle-'+label+'.png')))
 # Late views do not restart the beat; resources are released on reset/rematch.
 p.evaluate('sceneWall=1007000');p.wait_for_function('!scene.finale.active');p.evaluate('scene.clearActors()');assert p.evaluate('!scene.finale.effect&&scene.finale.resources.length===0')
 p.evaluate('scene.destroy()');assert not errors,errors;print('PASS contact framing, both bodies inside desktop/mobile settle shots, expired beat does not replay, particle resources and scene cleanup');b.close()
