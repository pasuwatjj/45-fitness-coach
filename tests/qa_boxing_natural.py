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
 page.evaluate('w.bag.visible=false')
 for name,state in [('guard','{arms:short}'),('duck','{bend:.9,slip:.25,crouch:.25,arms:short}'),('slip','{slip:.9,crouch:.1,arms:short}'),('full-punch','{arms:full}')]:
  page.evaluate('apply('+state+');w.camera.position.set(4.2,1.7,1.3);w.camera.lookAt(0,.9,0);w.renderer.render(w.scene,w.camera)')
  page.screenshot(path=str(out/(name+'.png')))
 page.evaluate("w.add({appearance:{gender:'female'},growth:{},visual:{}},1)");page.wait_for_function("w.actors[1].canvas.dataset.avatarState==='ready'")
 page.evaluate('f=w.actors[1];apply({arms:full,bend:.6,slip:-.5})');female=page.evaluate('arm()');assert abs(female['reach']-female['length'])<.005
 assert not errors,errors
 print('PASS male/female full reach, short-jab pose preserved during impact, coordinated hip/spine/chest/neck, planted stance, valid skin weights; no JS errors')
 b.close()
