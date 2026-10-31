/* Original cage scene. Shared Three.js renderer; approved profile avatar assets. */
'use strict';
window.CageFighter=class extends FitnessImportedAvatar{
 constructor(world,model,id){const canvas=document.createElement('canvas');super(canvas,world);this.world=world;this.id=id;this.target={x:0,z:0};this.position=new THREE.Vector2();this.state={};this.poseSmooth={bend:0,slip:0,crouch:0};this.set(model)}
 status(value){this.canvas.dataset.avatarState=value;this.world?.loading()}
 start(){this.running=true}stop(){this.running=false}schedule(){}draw(){}
 buildRig(deform){
  super.buildRig(deform);const T=THREE,hip=(deform(...this.assetRig.joints.leftLeg[0])[1]+deform(...this.assetRig.joints.rightLeg[0])[1])/2;
  this.hip=hip;this.spine=new T.Bone();this.spine.position.y=hip;this.skeleton.bones[0].add(this.spine);
  for(const side of ['left','right']){const upper=this.bones[side+'Arm'].upper;this.spine.add(upper);upper.position.y-=hip}
  this.spineIndex=this.skeleton.bones.length;this.skeleton.bones.push(this.spine);this.body.updateMatrixWorld(true);this.skeleton.calculateInverses();this.skeleton.init();
 }
 build(){
  super.build();if(!this.body)return;const T=THREE;
  for(const mesh of [...this.body.children]){
   if(mesh.isSkinnedMesh){const index=mesh.geometry.attributes.skinIndex,weight=mesh.geometry.attributes.skinWeight,position=mesh.geometry.attributes.position;
    for(let i=0;i<position.count;i++){const blend=T.MathUtils.clamp((position.getY(i)-this.hip)/.38,0,1);if(!blend)continue;let base=-1,empty=-1;
     for(let k=0;k<4;k++){if(index.array[i*4+k]===0&&weight.array[i*4+k]>0)base=k;if(weight.array[i*4+k]===0)empty=k}
     if(base>=0){const w=weight.array[i*4+base];if(blend===1||empty<0)index.array[i*4+base]=this.spineIndex;else{weight.array[i*4+base]=w*(1-blend);index.array[i*4+empty]=this.spineIndex;weight.array[i*4+empty]=w*blend}}
    }index.needsUpdate=true;weight.needsUpdate=true;mesh.castShadow=true;mesh.receiveShadow=true;
   }else if(mesh.isMesh){mesh.geometry.computeBoundingBox();const bottom=mesh.geometry.boundingBox.min.y*mesh.scale.y+mesh.position.y;if(bottom>this.hip+.2){this.spine.add(mesh);mesh.position.y-=this.hip}mesh.castShadow=true}
  }
  this.root.scale.setScalar(this.height*.5);this.body.updateMatrixWorld(true);
  const glove=this.material(this.id===0?'#252b36':'#3c2429',.7);
  for(const side of ['left','right']){const b=this.bones[side+'Arm'],grip=this.handGrips[side];if(!b||!grip)continue;const center=b.lower.worldToLocal(this.body.localToWorld(grip.center.clone()));this.ell(center.x,center.y,center.z,.135,.10,.16,glove,b.lower)}
 }
 punch(hand,token,type='straight'){if(this.punchToken===token)return;this.punchToken=token;this.punchHand=hand;this.punchType=type;this.punchAt=performance.now()}
 update(state,target,dt,time){
  if(!this.body)return;const T=THREE;this.state=state;this.target={x:state.x||0,z:state.z||0};const ease=1-Math.exp(-dt*15);this.position.lerp(new T.Vector2(this.target.x,this.target.z),ease);
  this.root.position.set(this.position.x,0,this.position.y);const yaw=Math.atan2(target.x-this.position.x,target.z-this.position.y);this.yaw=(this.yaw??yaw)+Math.atan2(Math.sin(yaw-(this.yaw??yaw)),Math.cos(yaw-(this.yaw??yaw)))*ease;this.root.rotation.y=this.yaw;
  this.phase=time;super.restPose();for(const key of ['bend','slip','crouch'])this.poseSmooth[key]+=(Number(state[key]||0)-this.poseSmooth[key])*ease;
  const pose=this.poseSmooth;this.spine.rotation.set(pose.bend*.75,0,-pose.slip*.52);this.body.position.set(0,-.06-.55*pose.crouch,0);
  for(const {name,bone}of this.fingers||[]){if(name.includes('leaf'))continue;const grip=this.handGrips[name.endsWith('_l')?'left':'right'];bone.quaternion.setFromAxisAngle(grip.axis,name.startsWith('thumb')?.6:1.3)}
  const elapsed=performance.now()-(this.punchAt??-1000),extension=elapsed<0||elapsed>380?0:elapsed<100?elapsed/100:elapsed<220?1:1-(elapsed-220)/160;
  // Rotate the chest and roll the striking shoulder with the punch, then recover.
  const twist=(this.punchHand==='left'?1:-1)*extension;
  this.spine.rotation.y=twist*(this.punchType==='hook'?.42:.25);
  this.spine.rotation.x+=extension*(this.punchType==='uppercut'?-.10:.12);
  this.spine.rotation.z-=twist*.09;
  for(const side of ['left','right']){
   const b=this.bones[side+'Arm'],sign=side==='left'?1:-1,measured=state.arms?.[side];if(!b)continue;
   const upper=new T.Vector3(...(measured?.upper||[sign*.25,-.5,.65])).normalize(),lower=new T.Vector3(...(measured?.lower||[-sign*.15,.8,.4])).normalize();
   const punch=this.punchHand===side?extension:0;
   if(punch){const path=this.punchType==='uppercut'?[[sign*.1,-.15,.8],[0,.85,.45]]:this.punchType==='hook'?[[sign*.55,.12,.7],[-sign*.6,.12,.8]]:[[sign*.06,.08,1],[0,.04,1]];upper.lerp(new T.Vector3(...path[0]).normalize(),punch).normalize();lower.lerp(new T.Vector3(...path[1]).normalize(),punch).normalize()}
   b.upper.scale.setScalar(1+.10*punch);const uq=new T.Quaternion().setFromUnitVectors(b.restUpper,upper),lq=uq.clone().invert().multiply(new T.Quaternion().setFromUnitVectors(b.restLower,lower));b.cageUpper??=uq.clone();b.cageLower??=lq.clone();b.cageUpper.slerp(uq,punch?.8:ease);b.cageLower.slerp(lq,punch?.8:ease);b.upper.quaternion.copy(b.cageUpper);b.lower.quaternion.copy(b.cageLower);
  }
  // Advance a shuffle cycle from actual displacement, so feet stop at cage/bag limits.
  const previous=this.previousStep,dx=previous?this.position.x-previous.x:0,dz=previous?this.position.y-previous.y:0;
  this.previousStep=this.position.clone();const speed=Math.min(1.3,Math.hypot(dx,dz)/Math.max(.001,dt));
  const requested=Math.hypot(state.move||0,state.strafe||0)>0;
  this.gait=(this.gait||0)+((requested?Math.min(1,speed/1.05):0)-(this.gait||0))*ease;
  this.stepPhase=(this.stepPhase||0)+speed*dt*9;
  const lateral=(state.strafe||0),forward=(state.move||0),phase=this.stepPhase,gait=this.gait;
  this.body.position.y+=Math.sin(phase*2)*.025*gait;
  for(const [side,sign]of [['left',1],['right',-1]]){
   const leg=this.bones[side+'Leg'];if(!leg)continue;const step=Math.sin(phase)*sign,lift=Math.max(0,step);
   leg.upper.rotation.z=sign*.10+step*.26*lateral*gait;
   leg.upper.rotation.x=-.10-.7*pose.crouch+step*.32*forward*gait;
   leg.lower.rotation.x=.20+1.35*pose.crouch+lift*.48*gait;
  }
 }
};
window.BoxingWorld=class{
 constructor(container){
  const T=THREE;this.container=container;this.events=new AbortController();this.resources=[];this.actors=[];this.states=[];this.running=true;this.yaw=.28;this.elevation=.30;this.distance=4.6;this.mode='side';this.focus=new T.Vector3(0,.9,0);this.last=performance.now();
  this.canvas=document.createElement('canvas');this.canvas.className='cage-canvas';this.canvas.setAttribute('aria-label',window.I18N?.lang==='en'?'3D boxing cage. Drag to orbit; scroll or pinch to zoom.':'สนามมวย 3 มิติ ลากเพื่อหมุนกล้อง เลื่อนหรือจีบสองนิ้วเพื่อซูม');this.canvas.tabIndex=0;container.append(this.canvas);
  this.notice=document.createElement('div');this.notice.className='cage-loading';container.append(this.notice);
  this.renderer=new T.WebGLRenderer({canvas:this.canvas,antialias:true,powerPreference:'high-performance'});this.renderer.outputColorSpace=T.SRGBColorSpace;this.renderer.toneMapping=T.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.25;this.renderer.shadowMap.enabled=true;this.renderer.shadowMap.type=T.PCFSoftShadowMap;
  this.scene=new T.Scene();this.scene.background=new T.Color('#09121f');this.scene.fog=new T.Fog('#09121f',15,34);this.camera=new T.PerspectiveCamera(43,1,.08,65);
  this.scene.add(new T.HemisphereLight(0xe6f1ff,0x586071,2.5));const sun=new T.DirectionalLight(0xfff3e1,4);sun.position.set(3,9,5);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);Object.assign(sun.shadow.camera,{left:-7,right:7,top:7,bottom:-7,near:.1,far:25});sun.shadow.bias=-.001;this.scene.add(sun);
  const fill=new T.DirectionalLight(0x98c9ff,2);fill.position.set(-5,5,-3);this.scene.add(fill);this.makeArena();this.bind();this.frame=requestAnimationFrame(t=>this.tick(t));
 }
 mat(color,extra={}){const m=new THREE.MeshStandardMaterial({color,roughness:.7,...extra});this.resources.push(m);return m}
 mesh(geometry,material,parent=this.scene){this.resources.push(geometry);const m=new THREE.Mesh(geometry,material);parent.add(m);return m}
 bar(a,b,r,material,parent=this.scene){const T=THREE,delta=new T.Vector3().subVectors(b,a),m=this.mesh(new T.CylinderGeometry(r,r,delta.length(),8),material,parent);m.position.copy(a).add(b).multiplyScalar(.5);m.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),delta.normalize());return m}
 makeArena(){
  const T=THREE,canvas=document.createElement('canvas');canvas.width=canvas.height=1024;const c=canvas.getContext('2d');c.fillStyle='#dbe0e1';c.fillRect(0,0,1024,1024);for(let i=0;i<9000;i++){const x=(i*73)%1024,y=(i*137)%1024;c.fillStyle=i%2?'#28384908':'#ffffff18';c.fillRect(x,y,2,2)}c.strokeStyle='#303e52';c.lineWidth=8;c.strokeRect(60,60,904,904);c.beginPath();c.arc(512,512,245,0,Math.PI*2);c.fillStyle='#e7a542';c.fill();c.textAlign='center';c.fillStyle='#142237';c.font='900 112px sans-serif';c.fillText('45 FIGHT',512,505);c.font='700 70px sans-serif';c.fillText('CLUB',512,590);const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;this.resources.push(texture);
  const floor=this.mesh(new T.CylinderGeometry(6,6,.22,8,1,false,Math.PI/8),this.mat('#d8dde3',{map:texture}));floor.position.y=-.12;floor.receiveShadow=true;
  const black=this.mat('#121922'),metal=this.mat('#6c7886',{metalness:.8,roughness:.35}),red=this.mat('#af3b3c'),blue=this.mat('#285a9d');this.fences=[];
  for(let i=0;i<8;i++){
   const a=(i+.5)*Math.PI/4,b=(i+1.5)*Math.PI/4,pa=new T.Vector3(Math.cos(a)*5.85,0,Math.sin(a)*5.85),pb=new T.Vector3(Math.cos(b)*5.85,0,Math.sin(b)*5.85),group=new T.Group();this.scene.add(group);this.fences.push({group,mid:pa.clone().add(pb).multiplyScalar(.5)});
   const post=this.mesh(new T.CylinderGeometry(.10,.10,2.5,12),i<4?red:blue,group);post.position.copy(pa);post.position.y=1.2;post.castShadow=true;
   for(const y of [.08,2.4])this.bar(pa.clone().setY(y),pb.clone().setY(y),.065,black,group);
   const length=pa.distanceTo(pb),lines=[];
   for(let x=-2.4;x<length+2.4;x+=.22)for(const sign of [-1,1]){
    let y0=Math.max(0,-x/sign),y1=Math.min(2.3,(length-x)/sign);if(sign<0){y0=Math.max(0,(length-x)/sign);y1=Math.min(2.3,-x/sign)}if(y1<=y0)continue;
    for(const y of [y0,y1]){const v=pa.clone().lerp(pb,(x+sign*y)/length);lines.push(v.x,y+.08,v.z)}
   }
   const geom=new T.BufferGeometry();geom.setAttribute('position',new T.Float32BufferAttribute(lines,3));this.resources.push(geom);const material=new T.LineBasicMaterial({color:'#71818e',transparent:true,opacity:.50});this.resources.push(material);group.add(new T.LineSegments(geom,material));
  }
  const skirt=this.mesh(new T.CylinderGeometry(6.05,6.15,.5,8,1,false,Math.PI/8),black);skirt.position.y=-.5;
  const crowdMat=this.mat('#182333'),geo=new T.SphereGeometry(.13,6,4);this.resources.push(geo);const crowd=new T.InstancedMesh(geo,crowdMat,112);const dummy=new T.Object3D();for(let i=0;i<112;i++){const row=Math.floor(i/56),a=Math.PI+(i%56)/55*Math.PI;dummy.position.set(Math.cos(a)*(7.8+row*.8),.4+row*.4,Math.sin(a)*(7.8+row*.8));dummy.scale.set(1,1.6,1);dummy.updateMatrix();crowd.setMatrixAt(i,dummy.matrix)}this.scene.add(crowd);
  const torsoGeo=new T.CylinderGeometry(.17,.22,.45,6);this.resources.push(torsoGeo);const bodies=new T.InstancedMesh(torsoGeo,crowdMat,112);for(let i=0;i<112;i++){crowd.getMatrixAt(i,dummy.matrix);dummy.matrix.decompose(dummy.position,dummy.quaternion,dummy.scale);dummy.position.y-=.32;dummy.scale.set(1,1,1);dummy.updateMatrix();bodies.setMatrixAt(i,dummy.matrix)}this.scene.add(bodies);


  this.lamps=[];this.beams=[];for(let i=0;i<8;i++){const a=i*Math.PI/4;const lamp=this.mesh(new T.BoxGeometry(.7,.13,.25),this.mat('#ffffff',{emissive:i%2?'#85bfff':'#fff3df',emissiveIntensity:3}));lamp.position.set(Math.cos(a)*4,5.5,Math.sin(a)*4);this.lamps.push(lamp);const beam=this.mesh(new T.ConeGeometry(1.3,5,16,1,true),new T.MeshBasicMaterial({color:i%2?0xa1c9ff:0xffe7bd,transparent:true,opacity:.018,depthWrite:false,side:T.DoubleSide}));this.resources.push(beam.material);beam.position.set(Math.cos(a)*3.5,3.0,Math.sin(a)*3.5);this.beams.push(beam)}
  this.bag=new T.Group();this.scene.add(this.bag);const leather=this.mat('#a34735',{roughness:.55});const bagBody=this.mesh(new T.CylinderGeometry(.28,.30,1.25,24),leather,this.bag);bagBody.position.y=1.0;bagBody.castShadow=true;const trim=this.mat('#242c38');for(const y of [.43,1.57]){const band=this.mesh(new T.CylinderGeometry(.30,.30,.12,24),trim,this.bag);band.position.y=y}const label=document.createElement('canvas');label.width=256;label.height=256;const bc=label.getContext('2d');bc.fillStyle='#252b36';bc.fillRect(0,0,256,256);bc.strokeStyle='#dfb775';bc.lineWidth=8;bc.strokeRect(12,12,232,232);bc.fillStyle='#fff0cf';bc.textAlign='center';bc.font='bold 100px sans-serif';bc.fillText('45',128,125);bc.font='bold 34px sans-serif';bc.fillText('FIGHT CLUB',128,188);const bt=new T.CanvasTexture(label);bt.colorSpace=T.SRGBColorSpace;this.resources.push(bt);const badge=this.mesh(new T.PlaneGeometry(.30,.35),this.mat('#fff',{map:bt}),this.bag);badge.position.set(0,1.1,.301);this.bar(new T.Vector3(0,1.65,0),new T.Vector3(0,4.7,0),.018,metal,this.bag);const base=this.mesh(new T.CylinderGeometry(.52,.58,.12,24),black,this.bag);base.position.y=.06;
 }
 bind(){
  const signal=this.events.signal,points=new Map();let pinch=0;
  this.canvas.style.touchAction='none';this.canvas.addEventListener('pointerdown',e=>{points.set(e.pointerId,{x:e.clientX,y:e.clientY});this.canvas.setPointerCapture(e.pointerId);if(points.size===2){const [a,b]=[...points.values()];pinch=Math.hypot(a.x-b.x,a.y-b.y)}},{signal});
  this.canvas.addEventListener('pointermove',e=>{const old=points.get(e.pointerId);if(!old)return;const dx=e.clientX-old.x,dy=e.clientY-old.y;points.set(e.pointerId,{x:e.clientX,y:e.clientY});this.mode='orbit';if(points.size===2){const [a,b]=[...points.values()],d=Math.hypot(a.x-b.x,a.y-b.y);if(pinch)this.distance=THREE.MathUtils.clamp(this.distance*pinch/Math.max(1,d),3.5,14);pinch=d}else{this.yaw-=dx*.008;this.elevation=THREE.MathUtils.clamp(this.elevation+dy*.005,.12,1.1)}},{signal});
  for(const event of ['pointerup','pointercancel','lostpointercapture'])this.canvas.addEventListener(event,e=>{points.delete(e.pointerId);pinch=0},{signal});
  this.canvas.addEventListener('wheel',e=>{e.preventDefault();this.distance=THREE.MathUtils.clamp(this.distance*Math.exp(e.deltaY*.001),3.5,14)},{signal,passive:false});
  this.canvas.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();this.mode='orbit';if(e.key==='ArrowLeft')this.yaw-=.12;if(e.key==='ArrowRight')this.yaw+=.12;if(e.key==='ArrowUp')this.distance=Math.max(3.5,this.distance-.3);if(e.key==='ArrowDown')this.distance=Math.min(14,this.distance+.3)}},{signal});
  this.canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();this.lost=true;this.notice.textContent=window.I18N?.lang==='en'?'Graphics interrupted; restoring…':'กราฟิกสะดุด กำลังกู้คืน…'},{signal});this.canvas.addEventListener('webglcontextrestored',()=>{this.lost=false;this.loading()},{signal});
 }
 view(mode){this.mode=mode;this.yaw=.28;this.elevation=mode==='top'?.95:.30;this.distance=mode==='top'?9:4.6}
 add(model,id){const actor=new CageFighter(this,model,id);this.actors.push(actor);return actor}
 clearActors(){for(const a of this.actors)a.destroy();this.actors=[];this.states=[];this.loading()}
 loading(){const error=this.actors.some(a=>a.canvas.dataset.avatarState==='error'),pending=this.actors.some(a=>a.canvas.dataset.avatarState!=='ready');this.notice.textContent=error?(window.I18N?.lang==='en'?'Avatar unavailable. Leave and reopen the arena to retry.':'โหลดตัวละครไม่ได้ ออกแล้วเปิดสนามใหม่เพื่อลองอีกครั้ง'):pending?(window.I18N?.lang==='en'?'Loading your fighters…':'กำลังโหลดตัวละครของคุณ…'):''}
 set(states,practice=true){this.states=states;this.practice=practice;this.bag.visible=practice;this.loading()}
 hitBag(){this.bagHit=performance.now()}
 project(x,z,y=1.65){const v=new THREE.Vector3(x,y,z).project(this.camera);return{x:(v.x*.5+.5)*100,y:(-.5*v.y+.5)*100}}
 tick(now){
  if(!this.running)return;this.frame=requestAnimationFrame(t=>this.tick(t));const dt=Math.min(.05,(now-this.last)/1000);this.last=now;if(document.hidden||this.lost)return;
  const T=THREE,rect=this.canvas.getBoundingClientRect();if(rect.width<2||rect.height<2)return;const ratio=Math.min(devicePixelRatio||1,1.5);if(this.width!==rect.width||this.height!==rect.height){this.width=rect.width;this.height=rect.height;this.renderer.setPixelRatio(ratio);this.renderer.setSize(rect.width,rect.height,false);this.camera.aspect=rect.width/rect.height;this.camera.updateProjectionMatrix()}
  const states=this.states;for(let i=0;i<this.actors.length;i++){const state=states[i]||{},target=states[1-i]||{x:0,z:0};this.actors[i].update(state,target,dt,now/1000)}
  let x=0,z=0;for(const s of states){x+=s.x||0;z+=s.z||0}const count=states.length||1;this.focus.lerp(new T.Vector3(x/count,.9,z/count),1-Math.exp(-dt*5));
  if(this.mode==='side'&&states.length===2){const dx=states[1].x-states[0].x,dz=states[1].z-states[0].z,desired=Math.atan2(-dz,dx)+.18;this.yaw+=Math.atan2(Math.sin(desired-this.yaw),Math.cos(desired-this.yaw))*(1-Math.exp(-dt*3))}
  if(this.mode==='follow'&&this.actors[this.selfIndex||0])this.yaw=this.actors[this.selfIndex||0].yaw+Math.PI+.30;
  const separation=states.length===2?Math.hypot(states[0].x-states[1].x,states[0].z-states[1].z):1;
  const radius=Math.max(this.distance,separation*1.15+2.5)/Math.min(1,Math.max(.6,this.camera.aspect));this.camera.position.set(this.focus.x+Math.sin(this.yaw)*radius*Math.cos(this.elevation),this.focus.y+Math.sin(this.elevation)*radius,this.focus.z+Math.cos(this.yaw)*radius*Math.cos(this.elevation));this.camera.lookAt(this.focus);
  for(const f of this.fences){const towardCamera=f.mid.clone().sub(this.focus).dot(this.camera.position.clone().sub(this.focus));f.group.visible=towardCamera<4}
  for(const lamp of this.lamps)lamp.visible=this.camera.position.y<5.3;for(const beam of this.beams)beam.visible=this.camera.position.y<5.3;
  const motion=!matchMedia('(prefers-reduced-motion: reduce)').matches&&document.body.dataset.effects!=='off';for(let i=0;i<this.beams.length;i++)this.beams[i].rotation.z=motion?Math.sin(now/2600+i)*.15:0;
  const elapsed=(now-(this.bagHit??-5000))/1000;this.bag.rotation.z=elapsed<2&&motion?Math.sin(elapsed*12)*Math.exp(-elapsed*3)*.12:0;
  this.renderer.render(this.scene,this.camera);
 }
 destroy(){this.running=false;cancelAnimationFrame(this.frame);this.events.abort();this.clearActors();for(const r of this.resources)r.dispose();this.renderer.dispose();this.renderer.forceContextLoss();this.container.replaceChildren()}
};
