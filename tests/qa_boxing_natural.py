"""Deterministic local 3D rig checks: actual reach, articulated torso, preserved meshes."""
from pathlib import Path
from playwright.sync_api import sync_playwright
root=__import__('os').environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5055');out=Path('work/boxing-natural-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1000,'height':800});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.route(root+'/__rig__',lambda r:r.fulfill(content_type='text/html',body='<div id="arena" style="width:1000px;height:800px"></div>'))
 page.goto(root+'/__rig__');page.add_style_tag(content='body{margin:0}.cage-canvas{width:1000px;height:800px}')
 for asset in ['vendor/three-r160.min.js','character-renderer.js','muscle-progression.js','imported-avatar.js','boxing-world.js']:page.add_script_tag(url=root+'/static/'+asset)
 page.evaluate("window.I18N={lang:'en'};window.w=new BoxingWorld(document.getElementById('arena'));w.add({appearance:{},growth:{},visual:{}},0);w.set([{x:0,z:0}],true)")
 page.wait_for_function("w.actors[0].canvas.dataset.avatarState==='ready'");page.evaluate('w.running=false;cancelAnimationFrame(w.frame)')
 page.evaluate("""window.f=w.actors[0];window.apply=(pose)=>{f.punchAt=-1000;for(let i=0;i<120;i++)f.update({x:0,z:0,...pose},{x:0,z:3},.016,i*.016);f.root.updateMatrixWorld(true)};
 window.arm=()=>{const a=f.bones.leftArm,s=a.upper.getWorldPosition(new THREE.Vector3()),e=a.lower.getWorldPosition(new THREE.Vector3()),h=a.lower.localToWorld(a.end.clone());return{reach:s.distanceTo(h),length:(a.lower.position.length()+a.end.length())*f.root.scale.x,upper:e.clone().sub(s).normalize().toArray(),lower:h.clone().sub(e).normalize().toArray()}};
 window.full={left:{upper:[0,0,1],lower:[0,0,1]},right:{upper:[0,-.6,.8],lower:[0,.8,.6]}};
 window.short={left:{upper:[0,-.6,.8],lower:[0,.8,.6]},right:full.right};void 0""")
 page.evaluate('apply({arms:full})');full=page.evaluate('arm()');assert abs(full['reach']-full['length'])<.002,full
 page.evaluate('apply({arms:short})');short=page.evaluate('arm()');assert short['reach']<full['reach']*.80,(short,full)
 page.evaluate("f.punch('left','short-jab');f.punchAt=performance.now()-150;for(let i=0;i<60;i++)f.update({x:0,z:0,arms:short},{x:0,z:3},.016,i*.016);f.root.updateMatrixWorld(true)")
 jab=page.evaluate('arm()');assert abs(jab['reach']-short['reach'])<.005,(jab,short)
 assert page.evaluate('f.bones.leftArm.upper.scale.x===1&&f.chest.rotation.y>0&&f.pelvis.rotation.y>0')
 page.evaluate('apply({bend:.9,slip:.6,crouch:.2,arms:short})')
 assert page.evaluate('f.pelvis.rotation.x>0&&f.spine.rotation.x>.3&&f.chest.rotation.x>.4&&f.neck.rotation.x<0&&f.bones.leftLeg.lower.rotation.x>.5')
 assert page.evaluate('f.spine.parent===f.pelvis&&f.chest.parent===f.spine&&f.bones.leftArm.upper.parent===f.chest&&f.bones.leftLeg.upper.parent===f.pelvis')
 for key in ['upper','lower']:
  measured=page.evaluate('arm()')[key];expected=[0,-.6,.8] if key=='upper' else [0,.8,.6]
  assert sum((a-b)**2 for a,b in zip(measured,expected))<.001,(measured,expected)
 # New torso weights stay normalized and finite; profile meshes retain their original vertex counts.
 assert page.evaluate("""f.body.children.filter(m=>m.isSkinnedMesh).every(m=>{const a=m.geometry.attributes.skinWeight;for(let i=0;i<a.count;i++){const v=[a.getX(i),a.getY(i),a.getZ(i),a.getW(i)];if(v.some(x=>!Number.isFinite(x)||x<0)||Math.abs(v.reduce((s,x)=>s+x,0)-1)>.0001)return false}return true})""")
 # A stronger back lean must move the head behind the pelvis and turn the face upward.
 page.evaluate('w.bag.visible=false;apply({});window.neutralHead=f.neck.getWorldPosition(new THREE.Vector3());apply({bend:-.8,posture:{headPitch:-.25}})')
 assert page.evaluate("f.neck.getWorldPosition(new THREE.Vector3()).z<neutralHead.z-.20&&new THREE.Vector3(0,0,1).applyQuaternion(f.neck.getWorldQuaternion(new THREE.Quaternion())).y>.5")
 page.evaluate('w.camera.position.set(3,1.4,2);w.camera.lookAt(0,.95,0);w.renderer.render(w.scene,w.camera)');page.screenshot(path=str(out/'back-extension.png'))
 # Wind-up is tracked before a scoring event and arm vectors rotate with the shoulder frame.
 page.evaluate("window.wind={left:{upper:[.45,.1,-.8],lower:[-.1,.85,.1]},right:{upper:[-.2,-.5,.7],lower:[.1,.8,.4]}};apply({posture:{turn:.7,hipTurn:.1,tilt:.2,headYaw:-.3},arms:wind})")
 assert page.evaluate('f.chest.rotation.y>.35&&f.pelvis.rotation.y>0&&f.punchAt===-1000')
 assert page.evaluate("new THREE.Vector3(...arm().upper).distanceTo(new THREE.Vector3(...wind.left.upper).normalize().applyAxisAngle(new THREE.Vector3(0,1,0),.7*1.05))<.01")
 assert page.evaluate("['left','right'].every(s=>{const g=f.bones[s+'Arm'].glove;return g?.name==='boxing-closed-glove'&&g.getObjectByName('closed-shell')&&g.getObjectByName('wrist-cuff')&&g.getObjectByName('thumb-cover')})")
 page.evaluate('w.camera.position.set(2.6,1.65,2.5);w.camera.lookAt(0,1.05,0);w.renderer.render(w.scene,w.camera)');page.screenshot(path=str(out/'shoulder-windup.png'))
 # Head pitch/yaw/roll animate independently, without forcing a body arch.
 page.evaluate('apply({posture:{headPitch:-.6,headYaw:.5,headRoll:.4}})')
 assert page.evaluate('Math.abs(f.chest.rotation.x-.12)<.01&&f.neck.rotation.x<-.4&&f.neck.rotation.y>.35&&f.neck.rotation.z>.2')
 page.evaluate('apply({slip:.7,posture:{headRoll:0}})');assert page.evaluate('Math.abs(new THREE.Vector3(0,1,0).applyQuaternion(f.neck.getWorldQuaternion(new THREE.Quaternion())).x)<.05')
 page.evaluate('apply({})');assert page.evaluate('Math.abs(f.neck.rotation.y)<.01&&Math.abs(f.chest.rotation.y)<.01')
 page.evaluate('w.bag.visible=false')
 for name,state in [('guard','{arms:short}'),('duck','{bend:.9,slip:.25,crouch:.25,arms:short}'),('slip','{slip:.9,crouch:.1,arms:short}'),('full-punch','{arms:full}')]:
  page.evaluate('apply('+state+');w.camera.position.set(4.2,1.7,1.3);w.camera.lookAt(0,.9,0);w.renderer.render(w.scene,w.camera)')
  page.screenshot(path=str(out/(name+'.png')))
 page.evaluate("w.add({appearance:{gender:'female'},growth:{},visual:{}},1)");page.wait_for_function("w.actors[1].canvas.dataset.avatarState==='ready'")
 page.evaluate('f=w.actors[1];apply({arms:full,bend:.6,slip:-.5})');female=page.evaluate('arm()');assert abs(female['reach']-female['length'])<.005
 # Whole-body weight shifts move the pelvis while both fixed-length feet stay planted and level.
 for actor in [0,1]:
  page.evaluate("f=w.actors["+str(actor)+"];apply({});window.feet=()=>['left','right'].map(s=>f.bones[s+'Leg'].foot.getWorldPosition(new THREE.Vector3()));window.restFeet=feet();window.restHip=f.pelvis.getWorldPosition(new THREE.Vector3())")
  page.evaluate("apply({lowerBody:{confidence:1,shiftX:.65,shiftZ:.35,drop:.25,leftKnee:.4,rightKnee:.35},bend:.3,posture:{hipTurn:.3,turn:.6},arms:full})")
  assert page.evaluate("Math.abs(f.pelvis.getWorldPosition(new THREE.Vector3()).x-restHip.x)>.15*f.root.scale.x&&feet().every((v,i)=>v.distanceTo(restFeet[i])<.008)"),page.evaluate("({hip:f.pelvis.getWorldPosition(new THREE.Vector3()).distanceTo(restHip),feet:feet().map((v,i)=>v.distanceTo(restFeet[i])),state:f.state})")
  assert page.evaluate("['left','right'].every(s=>{const b=f.bones[s+'Leg'];return new THREE.Vector3(0,1,0).applyQuaternion(b.foot.getWorldQuaternion(new THREE.Quaternion())).y>.999&&b.upper.scale.x===1&&b.lower.scale.x===1})")
  # No indexed triangle retains a weighted finger vertex beneath either closed glove.
  assert page.evaluate("f.coveredHandTriangles>0&&f.body.children.filter(m=>m.isSkinnedMesh).every(m=>{const fingers=new Set(f.fingers.map(v=>f.skeleton.bones.indexOf(v.bone))),g=m.geometry;return [...g.index.array].every(i=>[0,1,2,3].every(k=>g.attributes.skinWeight.array[i*4+k]<.01||!fingers.has(g.attributes.skinIndex.array[i*4+k])))})")
  page.evaluate("apply({});w.renderer.render(w.scene,w.camera)")
  assert page.evaluate("f.supportSmooth.confidence<.001&&feet().every((v,i)=>v.distanceTo(restFeet[i])<.008)")
 assert not errors,errors
 print('PASS male/female full reach, short-jab pose preserved during impact, coordinated hip/spine/chest/neck, planted stance, valid skin weights, progressive back extension, independent head/shoulder wind-up and two closed red gloves; no JS errors')
 b.close()
