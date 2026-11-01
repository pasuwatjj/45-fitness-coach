"""Deterministic real-asset computer choreography and tracking isolation checks."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os,json
root=os.environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5066');out=Path('work/boxing-combat-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']);page=b.new_page(viewport={'width':1000,'height':800});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.route(root+'/__kick__',lambda r:r.fulfill(content_type='text/html',body='<div id="arena" style="width:1000px;height:800px"></div>'));page.goto(root+'/__kick__');page.add_style_tag(content='body{margin:0}.cage-canvas{width:1000px;height:800px}')
 for asset in ['vendor/three-r160.min.js','character-renderer.js','muscle-progression.js','imported-avatar.js','boxing-motion.js','boxing-world.js']:page.add_script_tag(url=root+'/static/'+asset)
 page.evaluate("window.I18N={lang:'en'};window.w=new BoxingWorld(document.getElementById('arena'));w.add({appearance:{},growth:{},visual:{}},0);w.add({appearance:{gender:'female'},growth:{},visual:{}},1);w.set([{x:0,z:0},{x:3,z:0}],false)")
 page.wait_for_function("w.actors.every(a=>a.canvas.dataset.avatarState==='ready')");page.evaluate("""w.running=false;cancelAnimationFrame(w.frame);w.bag.visible=false;
 window.apply=(f,kind,side='left',age=280,state={})=>{const clock=performance.now;performance.now=()=>10000;try{f.punchType=kind;f.punchHand=side;f.punchAt=kind==='none'?-1000:10000-age;for(let i=0;i<35;i++)f.update({x:0,z:0,controlMode:'computer',...state},{x:0,z:3},.016,0);f.root.updateMatrixWorld(true)}finally{performance.now=clock}};
 window.foot=(f,s)=>f.bones[s+'Leg'].foot.getWorldPosition(new THREE.Vector3());
 window.arm=(f,s)=>{const a=f.bones[s+'Arm'];return a.upper.getWorldPosition(new THREE.Vector3()).distanceTo(a.lower.localToWorld(a.end.clone()))/((a.lower.position.length()+a.end.length())*f.root.scale.x)};void 0""")
 measurements=[]
 for actor in [0,1]:
  page.evaluate('f=w.actors['+str(actor)+'];f.kickObstacles=[];w.actors[1-'+str(actor)+'].root.visible=false;f.root.visible=true;w.camera.position.set(3,1.6,3);w.camera.lookAt(0,.9,.2)')
  page.evaluate("apply(f,'none');window.idleHead=f.neck.getWorldPosition(new THREE.Vector3());window.idlePelvis=f.pelvis.rotation.clone()")
  assert page.evaluate("['left','right'].every(s=>f.bones[s+'Arm'].elbow?.isBone&&f.bones[s+'Arm'].glove.getObjectByName('mma-pad'))")
  assert page.evaluate('f.pelvis.rotation.x+f.spine.rotation.x+f.chest.rotation.x>.35&&f.bones.leftLeg.lower.rotation.x>.35')
  page.evaluate('w.renderer.render(w.scene,w.camera)');page.screenshot(path=str(out/f'stance-{actor}.png'))
  for side in ['left','right']:
   page.evaluate("s=>{apply(f,'none',s);window.stand=foot(f,s);window.support=foot(f,s==='left'?'right':'left');apply(f,'kick',s,280)}",side)
   metrics=page.evaluate("s=>{const a=foot(f,s),b=foot(f,s==='left'?'right':'left'),leg=f.bones[s+'Leg'],hip=leg.upper.getWorldPosition(new THREE.Vector3()),length=(leg.lower.position.length()+leg.end.length())*f.root.scale.x;return{height:a.y/f.height,extension:hip.distanceTo(a)/length,supportDrift:b.distanceTo(support),hipTurn:f.pelvis.rotation.y,chestTurn:f.chest.rotation.y}}",side);measurements.append(metrics)
   assert page.evaluate("s=>{const leg=f.bones[s+'Leg'],shin=leg.foot.getWorldPosition(new THREE.Vector3()).sub(leg.lower.getWorldPosition(new THREE.Vector3())).normalize(),toes=new THREE.Vector3(0,0,1).applyQuaternion(leg.foot.getWorldQuaternion(new THREE.Quaternion()));return shin.dot(toes)>.98}",side)
   assert metrics['height']>1.35 and metrics['extension']>.96 and metrics['supportDrift']<.01,metrics
   assert page.evaluate("['left','right'].every(s=>f.bones[s+'Leg'].upper.scale.x===1&&f.bones[s+'Leg'].lower.scale.x===1)")
   if side=='left':
    for age,label in [(100,'chamber'),(280,'kick'),(520,'recoil'),(760,'replant')]:
     page.evaluate("age=>{apply(f,'kick','left',age);w.renderer.render(w.scene,w.camera)}",age);page.screenshot(path=str(out/f'{label}-{actor}.png'))
   page.evaluate("s=>apply(f,'none',s)",side);assert page.evaluate('s=>foot(f,s).distanceTo(stand)<.01',side)
   page.evaluate("s=>apply(f,'straight',s,180)",side);assert page.evaluate('s=>arm(f,s)>.98',side)
   assert page.evaluate("s=>(s==='left'?-1:1)*f.pelvis.rotation.y>.15",side)
  page.evaluate("apply(f,'straight','left',180);w.renderer.render(w.scene,w.camera)");page.screenshot(path=str(out/f'punch-{actor}.png'))
  page.evaluate("apply(f,'none','left',0,{dashVisualUntil:10100});w.renderer.render(w.scene,w.camera)");assert page.evaluate('f.neck.getWorldPosition(new THREE.Vector3()).y<idleHead.y-.15');page.screenshot(path=str(out/f'dash-{actor}.png'))
  # Tracking never adopts canned kicks, baseline computer stance, or keyboard arm extension.
  page.evaluate("apply(f,'kick','left',280,{controlMode:'tracking'});window.trackedHead=f.neck.getWorldPosition(new THREE.Vector3())")
  assert page.evaluate('f.kickAmount===0&&trackedHead.y>idleHead.y+.05&&f.pelvis.rotation.y===0')
  # Foot contact at the bag still constrains penetration and permits withdrawal.
  page.evaluate("window.bagShape={a:new THREE.Vector3(0,.7,0),b:new THREE.Vector3(0,1.3,0),radius:.3,kind:'bag'};f.kickObstacles=[bagShape];apply(f,'none','left',0,{z:-1.05});apply(f,'kick','left',280,{z:-1.05})")
  assert page.evaluate('BoxingContact.distance(foot(f,"left"),bagShape)>=.11*f.height-.025')
  page.evaluate("apply(f,'none','left',0,{z:-1.05})");assert page.evaluate('foot(f,"left").y<.15*f.height')
 assert not errors,errors
 (out/'measurements.json').write_text(json.dumps(measurements,indent=2))
 print('PASS male/female high-kick phases and >96% leg extension, planted support, fixed lengths, full punches with hip drive, lowered dash, tracking isolation, contact and recovery; no JS errors')
 b.close()
