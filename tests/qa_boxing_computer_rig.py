"""Real asset checks for computer kicks, planted support leg, contact and recovery."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os
root=os.environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5064');out=Path('work/boxing-lobby-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']);page=b.new_page(viewport={'width':1000,'height':800});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.route(root+'/__kick__',lambda r:r.fulfill(content_type='text/html',body='<div id="arena" style="width:1000px;height:800px"></div>'));page.goto(root+'/__kick__');page.add_style_tag(content='body{margin:0}.cage-canvas{width:1000px;height:800px}')
 for asset in ['vendor/three-r160.min.js','character-renderer.js','muscle-progression.js','imported-avatar.js','boxing-world.js']:page.add_script_tag(url=root+'/static/'+asset)
 page.evaluate("window.I18N={lang:'en'};window.w=new BoxingWorld(document.getElementById('arena'));w.add({appearance:{},growth:{},visual:{}},0);w.add({appearance:{gender:'female'},growth:{},visual:{}},1);w.set([{x:0,z:0},{x:3,z:0}],false)")
 page.wait_for_function("w.actors.every(a=>a.canvas.dataset.avatarState==='ready')");page.evaluate("w.running=false;cancelAnimationFrame(w.frame);w.bag.visible=false;window.apply=(f,kind,side='left',z=0)=>{f.punchType=kind;f.punchHand=side;f.punchAt=kind==='kick'?performance.now()-280:-1000;for(let i=0;i<35;i++)f.update({x:0,z},{x:0,z:3},.016,0);f.root.updateMatrixWorld(true)};window.foot=(f,s)=>f.bones[s+'Leg'].foot.getWorldPosition(new THREE.Vector3());void 0")
 for actor in [0,1]:
  page.evaluate('f=w.actors['+str(actor)+'];f.kickObstacles=[];w.actors[1-'+str(actor)+'].root.visible=false;f.root.visible=true')
  for side in ['left','right']:
   page.evaluate("s=>{apply(f,'none',s);window.stand=foot(f,s);window.support=foot(f,s==='left'?'right':'left');apply(f,'kick',s)}",side)
   assert page.evaluate("s=>{const a=foot(f,s),b=foot(f,s==='left'?'right':'left');return a.y>stand.y+.3*f.height&&a.z>stand.z+.35*f.height&&b.distanceTo(support)<.01}",side)
   assert page.evaluate("['left','right'].every(s=>f.bones[s+'Leg'].upper.scale.x===1&&f.bones[s+'Leg'].lower.scale.x===1)")
   if side=='left':
    page.evaluate('w.camera.position.set(3,1.6,3);w.camera.lookAt(0,.9,.2);w.renderer.render(w.scene,w.camera)');page.screenshot(path=str(out/f'kick-{actor}.png'))
   page.evaluate("s=>apply(f,'none',s)",side);assert page.evaluate('s=>foot(f,s).distanceTo(stand)<.01',side)
  # The striking foot stays outside a bag capsule and withdraws freely.
  page.evaluate("window.bagShape={a:new THREE.Vector3(0,.7,0),b:new THREE.Vector3(0,1.3,0),radius:.3,kind:'bag'};f.kickObstacles=[bagShape];apply(f,'none','left',-1.05);apply(f,'kick','left',-1.05)")
  assert page.evaluate('BoxingContact.distance(foot(f,"left"),bagShape)>=.11*f.height-.025')
  page.evaluate("apply(f,'none','left',-1.05)");assert page.evaluate('foot(f,"left").y<.15*f.height')
 assert not errors,errors
 print('PASS male/female left/right kick articulation, planted support foot, fixed leg lengths, bag-foot contact and return to stance; no JS errors')
 b.close()
