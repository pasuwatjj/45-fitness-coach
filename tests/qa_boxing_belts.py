"""Read-only local rig checks for timed knockdown/recovery and the 45 belt ceremony."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os
root=os.environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5057');out=Path('work/boxing-belts-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1000,'height':800});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.route(root+'/__belts__',lambda r:r.fulfill(content_type='text/html',body='<div id="arena" style="width:1000px;height:800px"></div>'))
 page.goto(root+'/__belts__');page.add_style_tag(content='body{margin:0}.cage-canvas{width:1000px;height:800px}')
 for asset in ['vendor/three-r160.min.js','character-renderer.js','muscle-progression.js','imported-avatar.js','boxing-world.js']:page.add_script_tag(url=root+'/static/'+asset)
 page.evaluate("window.I18N={lang:'en'};window.w=new BoxingWorld(document.getElementById('arena'));w.add({appearance:{},growth:{},visual:{}},0);w.set([{x:0,z:0}],false)")
 page.wait_for_function("w.actors[0].canvas.dataset.avatarState==='ready'");page.evaluate('w.running=false;cancelAnimationFrame(w.frame)')
 page.evaluate("""window.f=w.actors[0];window.pose=(kind,age,recover=10)=>{const state={x:0,z:0,presentation:kind,presentationAt:performance.now()-age*1000,recoverAfter:recover};for(let i=0;i<60;i++)f.update(state,{x:0,z:3},.016,i*.016);f.root.updateMatrixWorld(true)};
 window.draw=()=>{w.camera.position.set(3.1,1.5,3.4);w.camera.lookAt(0,.9,0);w.renderer.render(w.scene,w.camera)};void 0""")
 page.evaluate("pose('down',1.5);draw()");assert page.evaluate("f.canvas.dataset.presentation==='lying'&&f.downAmount>.99")
 seated=page.evaluate('f.body.position.y');assert seated>.10,seated
 assert page.evaluate("['left','right'].every(s=>{const leg=f.bones[s+'Leg'];return leg.lower.localToWorld(leg.end.clone()).y>.01})")
 page.screenshot(path=str(out/'lying.png'))
 page.evaluate("pose('down',9);draw()");assert page.evaluate("f.canvas.dataset.presentation==='rising'&&f.downAmount>0&&f.downAmount<1")
 assert page.evaluate('f.body.position.y')<seated
 page.screenshot(path=str(out/'rising.png'))
 page.evaluate("pose('down',9.95);draw()");assert page.evaluate("f.canvas.dataset.presentation==='ready'&&f.downAmount===0")
 page.evaluate("pose(null,0);draw()");assert page.evaluate("f.canvas.dataset.presentation==='fighting'&&Math.abs(f.body.position.y)<.1")
 page.evaluate("pose('down',50,null)");assert page.evaluate("f.canvas.dataset.presentation==='lying'")
 page.evaluate("pose('champion',2);draw()");page.wait_for_function('f.belt.visible&&f.belt.children.some(m=>m.material?.map?.image?.complete)');page.evaluate('draw()')
 assert page.evaluate("Math.abs(f.root.rotation.y)<.05&&f.belt.parent===f.pelvis&&f.bones.rightArm.lower.getWorldPosition(new THREE.Vector3()).y>1.5")
 page.screenshot(path=str(out/'champion.png'))
 page.evaluate("pose(null,0)");assert page.evaluate('!f.belt.visible')
 page.evaluate("w.add({appearance:{gender:'female'},growth:{},visual:{}},1)");page.wait_for_function("w.actors[1].canvas.dataset.avatarState==='ready'")
 page.evaluate("f=w.actors[1];pose('down',2);draw()");assert page.evaluate('f.downAmount>.99')
 page.evaluate("pose('champion',2)");page.wait_for_function('f.belt.visible&&f.belt.children.some(m=>m.material?.map?.image?.complete)')
 page.evaluate('w.destroy()');assert page.locator('#arena canvas').count()==0
 assert not errors,errors
 print('PASS timed lying knockdown, grounded feet, recovery, final KO stays down, male/female champion belt and victory pose, cleanup; no JS errors')
 b.close()
