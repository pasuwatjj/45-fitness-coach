"""Browser checks for body-relative camera tracking and fixed-length contact constraints."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os
root=os.environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5058');out=Path('work/boxing-contact-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1100,'height':750});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.route(root+'/__contacts__',lambda r:r.fulfill(content_type='text/html',body='<div id="arena" style="width:1100px;height:750px"></div>'))
 page.goto(root+'/__contacts__');page.add_style_tag(content='body{margin:0}.cage-canvas{width:1100px;height:750px}')
 for asset in ['vendor/three-r160.min.js','character-renderer.js','muscle-progression.js','imported-avatar.js','boxing-pose.js','boxing-motion.js','boxing-world.js']:page.add_script_tag(url=root+'/static/'+asset)
 page.evaluate("window.I18N={lang:'en'};window.w=new BoxingWorld(document.getElementById('arena'));w.add({appearance:{},growth:{},visual:{}},0);w.set([{x:0,z:-.65}],true)")
 page.wait_for_function("w.actors[0].canvas.dataset.avatarState==='ready'");page.evaluate('w.running=false;cancelAnimationFrame(w.frame)')
 page.evaluate("""window.f=w.actors[0];window.full={left:{upper:[0,0,1],lower:[0,0,1]},right:{upper:[0,0,1],lower:[0,0,1]}};
 window.apply=(state)=>{for(let i=0;i<100;i++)f.update({x:0,z:-.65,...state},{x:0,z:1},.016,i*.016);f.root.updateMatrixWorld(true)};
 window.hand=(side)=>{const a=f.bones[side+'Arm'];return a.lower.localToWorld(a.contactEnd.clone())};
 window.bag=[{a:new THREE.Vector3(0,.7,0),b:new THREE.Vector3(0,1.3,0),radius:.30,kind:'bag'}];
 window.draw=()=>{w.camera.position.set(2.8,1.65,2.1);w.camera.lookAt(0,.9,-.2);w.renderer.render(w.scene,w.camera)};void 0""")
 page.evaluate('apply({arms:full});BoxingContact.constrain(f,bag);draw()')
 assert page.evaluate("['left','right'].every(s=>f.contacts[s]==='bag'&&BoxingContact.distance(hand(s),bag[0])>=.09)"),page.evaluate("({contacts:f.contacts,left:hand('left'),right:hand('right')})")
 assert page.evaluate("['left','right'].every(s=>f.bones[s+'Arm'].upper.scale.x===1)")
 page.screenshot(path=str(out/'bag-contact.png'))
 # The sweep catches a target crossed in one frame, even when the final point is beyond it.
 assert page.evaluate("BoxingContact.sweep(new THREE.Vector3(0,1,-1),new THREE.Vector3(0,1,1),bag[0],.095).z<-.39")
 assert page.evaluate("BoxingContact.segmentDistance(new THREE.Vector3(0,0,0),new THREE.Vector3(2,0,0),new THREE.Vector3(1,0,0),new THREE.Vector3(1,0,0))<1e-6")
 assert page.evaluate("BoxingContact.sweep(new THREE.Vector3(0,0,-1),new THREE.Vector3(0,0,1),{a:new THREE.Vector3(),b:new THREE.Vector3(),radius:.1},.095).z<-.19")
 # Retraction leaves the contact immediately, rather than sticking to it.
 page.evaluate("apply({arms:{left:{upper:[.3,-.8,.3],lower:[0,.8,.5]},right:{upper:[-.3,-.8,.3],lower:[0,.8,.5]}}});BoxingContact.constrain(f,bag)")
 assert page.evaluate("Object.keys(f.contacts).length===0")
 page.evaluate("w.bag.visible=false;apply({arms:full});window.barrier=[{a:new THREE.Vector3(-.5,1.38,-.22),b:new THREE.Vector3(.5,1.38,-.22),radius:.075,kind:'arm'}];BoxingContact.constrain(f,barrier)")
 assert page.evaluate("['left','right'].every(s=>f.contacts[s]==='arm'&&BoxingContact.distance(hand(s),barrier[0])>=.09)"),page.evaluate('f.contacts')
 # Real second avatar: both arm and torso/head volumes move with its current posture.
 page.evaluate("w.add({appearance:{gender:'female'},growth:{},visual:{}},1)");page.wait_for_function("w.actors[1].canvas.dataset.avatarState==='ready'")
 page.evaluate("window.other=w.actors[1];for(let i=0;i<100;i++)other.update({x:0,z:.15,arms:{left:{upper:[.3,.1,.8],lower:[0,.9,.2]},right:{upper:[-.3,.1,.8],lower:[0,.9,.2]}}},{x:0,z:-1},.016,i*.016);other.root.updateMatrixWorld(true);apply({arms:full});window.opponent=BoxingContact.shapes(other);BoxingContact.constrain(f,opponent);draw()")
 assert page.evaluate("Object.keys(f.contacts).length>0"),page.evaluate('f.contacts')
 assert page.evaluate("['left','right'].every(s=>opponent.every(c=>BoxingContact.distance(hand(s),c)>=.08))"),page.evaluate("opponent.map(c=>[c.kind,BoxingContact.distance(hand('left'),c)])")
 assert page.evaluate("['left','right'].every(s=>{const b=f.bones[s+'Arm'],shoulder=b.upper.getWorldPosition(new THREE.Vector3()),elbow=b.lower.getWorldPosition(new THREE.Vector3()),glove=hand(s);return opponent.every(c=>BoxingContact.segmentDistance(shoulder,elbow,c.a,c.b)>=c.radius+.065*f.height&&BoxingContact.segmentDistance(elbow,glove,c.a,c.b)>=c.radius+.065*f.height)})")
 page.screenshot(path=str(out/'guard-contact.png'))
 # Close over-shoulder framing follows the local player and keeps the target in view.
 page.evaluate("w.set([{x:0,z:-.65,arms:full},{x:0,z:.15}],false);w.selfIndex=0;w.view('follow');w.running=true;w.tick(performance.now()+40);w.running=false;cancelAnimationFrame(w.frame)")
 assert page.evaluate("w.mode==='follow'&&w.elevation<.15&&w.distance<3.5")
 # Settle the actual default framing at desktop and phone aspect ratios.
 for width,height in [(1100,750),(390,620)]:
  page.set_viewport_size({'width':width,'height':height});page.add_style_tag(content=f'#arena,.cage-canvas{{width:{width}px!important;height:{height}px!important}}')
  page.evaluate("w.set([{x:-.7,z:0},{x:.7,z:0}],false);const draw=w.renderer.render.bind(w.renderer);w.renderer.render=()=>{};w.running=true;for(let i=0;i<150;i++){w.tick(w.last+16);cancelAnimationFrame(w.frame)}w.running=false;w.renderer.render=draw;draw(w.scene,w.camera)")
  assert page.evaluate("w.actors.every(a=>{const v=a.neck.getWorldPosition(new THREE.Vector3()).project(w.camera);return Math.abs(v.x)<.95&&Math.abs(v.y)<.95})")
  page.screenshot(path=str(out/f'boxing-camera-{width}.png'))
 assert not errors,errors
 print('PASS bag/arm/body contact, no fast-punch tunnelling, fixed arm lengths, release on retract, two-avatar guard geometry and close boxing camera; no JS errors')
 b.close()
