/* Original cage scene. Shared Three.js renderer; approved profile avatar assets. */
'use strict';
// Kinematic contact constraints preserve the tracked pose until an arm meets a surface.
window.BoxingContact={
 closest(point,a,b){const d=b.clone().sub(a),t=THREE.MathUtils.clamp(point.clone().sub(a).dot(d)/Math.max(1e-9,d.lengthSq()),0,1);return a.clone().addScaledVector(d,t)},
 distance(point,c){return point.distanceTo(this.closest(point,c.a,c.b))-c.radius},
 sweep(from,to,c,radius){
  const delta=to.clone().sub(from),steps=Math.max(2,Math.ceil(delta.length()/.025)),gap=p=>this.distance(p,c)-radius;
  // Allow withdrawal from an existing contact; never keep a glove stuck to a surface.
  let last=0,previous=gap(from);if(previous<=.003&&gap(to)>previous+.001)return null;
  for(let i=1;i<=steps;i++){const t=i/steps,p=from.clone().addScaledVector(delta,t),d=gap(p);if(d<.003){let lo=last,hi=t;for(let n=0;n<12;n++){const mid=(lo+hi)/2;if(gap(from.clone().addScaledVector(delta,mid))<.003)hi=mid;else lo=mid}const hit=from.clone().addScaledVector(delta,lo),near=this.closest(hit,c.a,c.b),normal=hit.clone().sub(near);if(normal.lengthSq()<1e-8)normal.copy(from).sub(c.a);if(normal.lengthSq()<1e-8)normal.set(0,0,1);return hit.copy(near).addScaledVector(normal.normalize(),c.radius+radius+.004)}last=t;previous=d}return null;
 },
 shapes(actor){
  const T=THREE,point=(bone,v=[0,0,0])=>bone.localToWorld(new T.Vector3(...v)),h=actor.height;
  const arms=[];for(const side of ['left','right']){const b=actor.bones[side+'Arm'];if(!b)continue;const shoulder=point(b.upper),elbow=point(b.lower),hand=point(b.lower,b.contactEnd.toArray());arms.push({a:shoulder,b:elbow,radius:.075*h,kind:'arm',owner:actor},{a:elbow,b:hand,radius:.075*h,kind:'arm',owner:actor},{a:hand,b:hand,radius:.09*h,kind:'arm',owner:actor})}
  return [...arms,{a:point(actor.pelvis,[0,.20,0]),b:point(actor.chest,[0,.35,0]),radius:.21*h,kind:'body',owner:actor},{a:point(actor.neck,[0,.16,0]),b:point(actor.neck,[0,.38,0]),radius:.135*h,kind:'head',owner:actor}];
 },
 segmentDistance(a,b,c,d){
  const u=b.clone().sub(a),v=d.clone().sub(c),w=a.clone().sub(c),aa=u.dot(u),bb=u.dot(v),cc=v.dot(v),dd=u.dot(w),ee=v.dot(w),den=aa*cc-bb*bb,clamp=THREE.MathUtils.clamp;
  let s=den>1e-10?clamp((bb*ee-cc*dd)/den,0,1):0,t=cc>1e-10?(bb*s+ee)/cc:0;
  if(t<0){t=0;s=aa>1e-10?clamp(-dd/aa,0,1):0}else if(t>1){t=1;s=aa>1e-10?clamp((bb-dd)/aa,0,1):0}
  return a.clone().addScaledVector(u,s).distanceTo(c.clone().addScaledVector(v,t));
 },
 solve(actor,side,target,shapes=[]){
  const T=THREE,b=actor.bones[side+'Arm'],start=b.upper.getWorldPosition(new T.Vector3()),oldElbow=b.lower.getWorldPosition(new T.Vector3()),scale=actor.root.scale.x,l1=b.lower.position.length()*scale,l2=b.contactEnd.length()*scale;
  const axis=target.clone().sub(start),distance=T.MathUtils.clamp(axis.length(),Math.abs(l1-l2)+.0001,l1+l2-.0001);if(axis.lengthSq()<1e-10)axis.set(0,0,1);axis.normalize();target.copy(start).addScaledVector(axis,distance);
  const along=(l1*l1-l2*l2+distance*distance)/(2*distance),height=Math.sqrt(Math.max(0,l1*l1-along*along));
  const pole=oldElbow.sub(start).addScaledVector(axis,-oldElbow.dot(axis));
  if(pole.lengthSq()<1e-6){pole.set(side==='left'?.35:-.35,-1,0).applyQuaternion(actor.root.quaternion);pole.addScaledVector(axis,-pole.dot(axis))}
  if(pole.lengthSq()<1e-8)pole.set(1,0,0);pole.normalize();
  let elbow=start.clone().addScaledVector(axis,along).addScaledVector(pole,height);
  // Rotate the elbow around the reach axis when the forearm would cut through a guard.
  const clearance=e=>shapes.reduce((gap,c)=>Math.min(gap,this.segmentDistance(start,e,c.a,c.b)-c.radius-.075*actor.height,this.segmentDistance(e,target,c.a,c.b)-c.radius-.075*actor.height),Infinity);
  let best=clearance(elbow);
  if(best<.003)for(let i=1;i<16;i++){const e=start.clone().addScaledVector(axis,along).addScaledVector(pole.clone().applyAxisAngle(axis,i*Math.PI/8),height),gap=clearance(e);if(gap>best){elbow=e;best=gap}if(best>=.003)break}
  const inv=b.upper.parent.getWorldQuaternion(new T.Quaternion()).invert();
  const upper=elbow.clone().sub(start).normalize().applyQuaternion(inv),lower=target.clone().sub(elbow).normalize().applyQuaternion(inv),uq=new T.Quaternion().setFromUnitVectors(b.restUpper,upper);
  b.upper.quaternion.copy(uq);b.lower.quaternion.copy(uq.clone().invert().multiply(new T.Quaternion().setFromUnitVectors(b.contactEnd.clone().normalize(),lower)));actor.root.updateMatrixWorld(true);
 },
 constrain(actor,shapes){
  const T=THREE,contacts={};actor.contactPrevious??={};
  if(actor.state.presentation){actor.contactPrevious={};actor.contacts=contacts;return}
  for(const side of ['left','right']){
   const b=actor.bones[side+'Arm'];if(!b?.contactEnd)continue;
   let hand=b.lower.localToWorld(b.contactEnd.clone()),elbow=b.lower.getWorldPosition(new T.Vector3()),shoulder=b.upper.getWorldPosition(new T.Vector3()),target=hand.clone();const radius=.095*actor.height;
   // Sweep from the shoulder as well as the previous glove to avoid tunnelling at low FPS.
   for(const from of [shoulder,elbow,actor.contactPrevious[side]].filter(Boolean)){
    let nearest=null,distance=Infinity;
    for(const c of shapes){const hit=this.sweep(from,target,c,radius);if(hit&&from.distanceToSquared(hit)<distance){nearest={hit,c};distance=from.distanceToSquared(hit)}}
    if(nearest){target.copy(nearest.hit);contacts[side]=nearest.c.kind}
   }
   for(let i=0;i<8;i++){const nx=Math.cos(i*Math.PI/4),nz=Math.sin(i*Math.PI/4),excess=target.x*nx+target.z*nz-(5.85*Math.cos(Math.PI/8)-radius);if(excess>0){target.x-=nx*excess;target.z-=nz*excess;contacts[side]='cage'}}
   if(target.y<radius){target.y=radius;contacts[side]='floor'}
   if(contacts[side]){
    this.solve(actor,side,target,shapes);
    // Correct endpoint overlap after the fixed-length IK solve; never scale the arm bones.
    for(let pass=0;pass<4;pass++){
     hand=b.lower.localToWorld(b.contactEnd.clone());let pushed=false;
     for(const c of shapes){const near=this.closest(hand,c.a,c.b),normal=hand.clone().sub(near),length=normal.length();if(length<c.radius+radius){if(length<1e-6)normal.copy(shoulder).sub(near);if(normal.lengthSq()<1e-8)normal.set(0,0,1);target.copy(near).addScaledVector(normal.normalize(),c.radius+radius+.004);this.solve(actor,side,target,shapes);hand=b.lower.localToWorld(b.contactEnd.clone());pushed=true;contacts[side]=c.kind}}
     if(!pushed)break;
    }
   }
   // If no elbow swivel clears a close obstacle, retract the chain until both links clear.
   for(let pass=0;pass<10;pass++){
    elbow=b.lower.getWorldPosition(new T.Vector3());hand=b.lower.localToWorld(b.contactEnd.clone());
    const obstruction=shapes.find(c=>this.segmentDistance(shoulder,elbow,c.a,c.b)<c.radius+.07*actor.height||this.segmentDistance(elbow,hand,c.a,c.b)<c.radius+.07*actor.height);
    if(!obstruction)break;contacts[side]=obstruction.kind;target.copy(hand).lerp(shoulder,.12);this.solve(actor,side,target,shapes);
   }
   actor.contactPrevious[side]=b.lower.localToWorld(b.contactEnd.clone());
  }
  actor.relaxElbows?.();actor.root.updateMatrixWorld(true);actor.contacts=contacts;
 }
};

window.CageFighter=class extends FitnessImportedAvatar{
 constructor(world,model,id){const canvas=document.createElement('canvas');super(canvas,world);this.world=world;this.id=id;this.target={x:0,z:0};this.position=new THREE.Vector2();this.state={};this.supportSmooth={confidence:0,shiftX:0,shiftZ:0,drop:0,hipRoll:0,leftKnee:0,rightKnee:0,stance:0,stagger:0};this.poseSmooth={bend:0,slip:0,crouch:0,turn:0,hipTurn:0,tilt:0,headPitch:0,headYaw:0,headRoll:0};this.set(model)}
 status(value){this.canvas.dataset.avatarState=value;this.world?.loading()}
 start(){this.running=true}stop(){this.running=false}schedule(){}draw(){}
 buildRig(deform){
  super.buildRig(deform);const T=THREE,hip=(deform(...this.assetRig.joints.leftLeg[0])[1]+deform(...this.assetRig.joints.rightLeg[0])[1])/2;
  this.hip=hip;this.shoulderHeight=deform(...this.assetRig.joints.leftArm[0])[1];
  const base=this.skeleton.bones[0];this.pelvis=new T.Bone();this.pelvis.position.y=hip;base.add(this.pelvis);
  this.spine=new T.Bone();this.spine.position.y=.22;this.pelvis.add(this.spine);
  this.chest=new T.Bone();this.chest.position.y=.42;this.spine.add(this.chest);
  this.neck=new T.Bone();this.neck.position.y=this.shoulderHeight+.12-hip-.64;this.chest.add(this.neck);
  for(const side of ['left','right']){
   const arm=this.bones[side+'Arm'].upper;this.chest.add(arm);arm.position.y-=hip+.64;this.bones[side+'Arm'].cageBindPosition=arm.position.clone();
   const leg=this.bones[side+'Leg'].upper;this.pelvis.add(leg);leg.position.y-=hip;
  }
  for(const side of ['left','right']){const arm=this.bones[side+'Arm'];arm.elbow=new T.Bone();arm.elbow.position.copy(arm.lower.position);arm.upper.add(arm.elbow);arm.elbowIndex=this.skeleton.bones.length;arm.upperIndex=this.skeleton.bones.indexOf(arm.upper);arm.lowerIndex=this.skeleton.bones.indexOf(arm.lower);arm.elbowBind=new T.Vector3(...deform(...this.assetRig.joints[side+'Arm'][1]));this.skeleton.bones.push(arm.elbow)}
  for(const name of ['pelvis','spine','chest','neck']){this[name+'Index']=this.skeleton.bones.length;this.skeleton.bones.push(this[name])}
  for(const side of ['left','right']){const leg=this.bones[side+'Leg'];leg.foot=new T.Bone();leg.foot.position.copy(leg.end);leg.lower.add(leg.foot);leg.footIndex=this.skeleton.bones.length;leg.lowerIndex=this.skeleton.bones.indexOf(leg.lower);leg.footBind=new T.Vector3(...deform(...this.assetRig.joints[side+'Leg'][2]));this.skeleton.bones.push(leg.foot)}
  this.body.updateMatrixWorld(true);this.skeleton.calculateInverses();this.skeleton.init();
 }
 build(){
  super.build();if(!this.body)return;this.belt=null;const T=THREE;
  for(const mesh of [...this.body.children]){
   if(mesh.isSkinnedMesh){const index=mesh.geometry.attributes.skinIndex,weight=mesh.geometry.attributes.skinWeight,position=mesh.geometry.attributes.position;
    // Reweight only the original root contribution; limb and finger weights stay authored.
    const zones=[[this.hip-.25,0],[this.hip+.05,this.pelvisIndex],[this.hip+.45,this.spineIndex],[this.shoulderHeight-.12,this.chestIndex],[this.shoulderHeight+.25,this.neckIndex]];
    for(let i=0;i<position.count;i++){
     const y=position.getY(i);let low=zones[0],high=zones[0];
     for(let j=1;j<zones.length;j++){low=zones[j-1];high=zones[j];if(y<=high[0])break}
     const blend=T.MathUtils.smoothstep(y,low[0],high[0]);let base=-1,empty=-1;
     for(let k=0;k<4;k++){if(index.array[i*4+k]===0&&weight.array[i*4+k]>0)base=k;if(weight.array[i*4+k]===0)empty=k}
     if(base<0)continue;const w=weight.array[i*4+base];
     index.array[i*4+base]=blend<.5?low[1]:high[1];
     if(empty>=0&&blend>0&&blend<1){index.array[i*4+base]=low[1];weight.array[i*4+base]=w*(1-blend);index.array[i*4+empty]=high[1];weight.array[i*4+empty]=w*blend}
    }
    // Preserve volume at the elbow: the local band follows a half-angle corrective joint,
    // instead of collapsing between two sharply opposing linear skin transforms.
    for(let i=0;i<position.count;i++)for(const side of ['left','right']){
     const arm=this.bones[side+'Arm'],v=new T.Vector3().fromBufferAttribute(position,i).sub(arm.elbowBind),along=v.dot(arm.restUpper),radial=v.clone().addScaledVector(arm.restUpper,-along).length();
     const blend=(1-T.MathUtils.smoothstep(Math.abs(along),.035,.20))*.85;if(blend<=0||radial>.30)continue;
     const weights=new Map();let transfer=0;for(let k=0;k<4;k++){const bone=index.array[i*4+k],w=weight.array[i*4+k];if(!w)continue;const moved=(bone===arm.upperIndex||bone===arm.lowerIndex)?w*blend:0;transfer+=moved;weights.set(bone,(weights.get(bone)||0)+w-moved)}
     if(transfer<=0)continue;weights.set(arm.elbowIndex,transfer);const entries=[...weights].sort((a,b)=>b[1]-a[1]).slice(0,4),sum=entries.reduce((n,e)=>n+e[1],0);for(let k=0;k<4;k++){index.array[i*4+k]=entries[k]?.[0]||0;weight.array[i*4+k]=(entries[k]?.[1]||0)/sum}
    }
    // A cage-only ankle joint keeps feet level while hips and knees absorb the lean.
    for(let i=0;i<position.count;i++)for(const side of ['left','right']){
     const leg=this.bones[side+'Leg'],blend=1-T.MathUtils.smoothstep(position.getY(i),leg.footBind.y,leg.footBind.y+.10);if(blend<=0)continue;
     let slot=-1,empty=-1;for(let k=0;k<4;k++){if(index.array[i*4+k]===leg.lowerIndex&&weight.array[i*4+k]>0)slot=k;if(weight.array[i*4+k]===0)empty=k}
     if(slot<0)continue;if(blend>.999){index.array[i*4+slot]=leg.footIndex}else if(empty>=0){const w=weight.array[i*4+slot];weight.array[i*4+slot]=w*(1-blend);weight.array[i*4+empty]=w*blend;index.array[i*4+empty]=leg.footIndex}
    }
    index.needsUpdate=true;weight.needsUpdate=true;mesh.castShadow=true;mesh.receiveShadow=true;
   }else if(mesh.isMesh){mesh.geometry.computeBoundingBox();const bottom=mesh.geometry.boundingBox.min.y*mesh.scale.y+mesh.position.y;if(bottom>this.hip+.2){this.neck.add(mesh);mesh.position.y-=this.shoulderHeight+.12}mesh.castShadow=true}
  }
  // Build glove attachment in the bind pose, before any animated posture is applied.
  this.root.scale.setScalar(this.height*.5);this.body.updateMatrixWorld(true);
  // Hide only cage hand triangles under the replacement MMA fist; profile meshes stay untouched.
  const wrists=['left','right'].map(side=>{const b=this.bones[side+'Arm'];return{lower:this.skeleton.bones.indexOf(b.lower),fingers:new Set(this.fingers.filter(f=>f.name.endsWith(side==='left'?'_l':'_r')).map(f=>this.skeleton.bones.indexOf(f.bone))),point:b.lower.localToWorld(b.end.clone()).applyMatrix4(this.body.matrixWorld.clone().invert()),direction:b.restLower.clone()}});
  this.coveredHandTriangles=0;
  for(const mesh of this.body.children.filter(m=>m.isSkinnedMesh)){
   const geometry=mesh.geometry,position=geometry.attributes.position,skin=geometry.attributes.skinIndex,weight=geometry.attributes.skinWeight,idx=geometry.index;if(!idx)continue;const covered=[];
   for(let i=0;i<position.count;i++){const v=new T.Vector3().fromBufferAttribute(position,i);covered[i]=wrists.some(w=>{let forearm=false;for(let k=0;k<4;k++){if(weight.array[i*4+k]<.01)continue;const bone=skin.array[i*4+k];if(w.fingers.has(bone))return true;if(bone===w.lower)forearm=true}const d=v.clone().sub(w.point);return forearm&&d.length()<.46&&d.dot(w.direction)>-.025})}
   const kept=[];for(let i=0;i<idx.count;i+=3){const a=idx.getX(i),b=idx.getX(i+1),c=idx.getX(i+2);if(covered[a]||covered[b]||covered[c])this.coveredHandTriangles++;else kept.push(a,b,c)}geometry.setIndex(kept);
  }
  const leather=this.material('#171d24',.58),seam=this.material('#38434d',.72),strap=this.material('#a82d3b',.65),exposed=this.material(this.model.appearance?.skin_color||'#d79f7a',.78);
  for(const side of ['left','right']){
   const b=this.bones[side+'Arm'],grip=this.handGrips[side];if(!b||!grip)continue;
   const center=b.lower.worldToLocal(this.body.localToWorld(grip.center.clone()));b.contactEnd=center.clone();
   const glove=new T.Group();glove.name='boxing-mma-glove';glove.position.copy(center);b.lower.add(glove);b.glove=glove;
   const y=center.clone().sub(b.end).normalize(),x=grip.across.clone().addScaledVector(y,-grip.across.dot(y)).normalize(),z=new T.Vector3().crossVectors(x,y).normalize();glove.quaternion.setFromRotationMatrix(new T.Matrix4().makeBasis(x,y,z));
   this.ell(0,-.015,.005,.10,.11,.065,exposed,glove).name='curled-fist';this.ell(0,.018,-.040,.115,.12,.045,leather,glove).name='mma-pad';
   for(let i=0;i<4;i++){const x=(i-1.5)*.052;this.ell(x,.102,-.018,.029,.045,.053,leather,glove).name='knuckle-pad';this.ell(x,.13,.045,.023,.037,.029,exposed,glove).name='exposed-finger'}
   this.ell(.108,-.026,.026,.038,.067,.045,exposed,glove).name='curled-thumb';this.ell(.101,-.055,-.009,.040,.055,.037,leather,glove).name='thumb-loop';
   const wrist=b.end.clone().sub(center).applyQuaternion(glove.quaternion.clone().invert());
   const cuff=this.mesh(new T.CylinderGeometry(.105,.11,.13,16),leather,glove);cuff.position.copy(wrist);cuff.name='wrist-cuff';
   const band=this.mesh(new T.CylinderGeometry(.109,.114,.048,16),strap,glove);band.position.copy(wrist);band.name='wrist-strap';
   const patch=this.mesh(new T.BoxGeometry(.085,.043,.012),seam,glove);patch.position.copy(wrist).add(new T.Vector3(0,0,.112));
  }
  this.root.updateMatrixWorld(true);
  for(const side of ['left','right']){const leg=this.bones[side+'Leg'];leg.footHome=this.root.worldToLocal(leg.lower.localToWorld(leg.end.clone()));leg.footHome.y=.06*this.height/this.root.scale.y;leg.footHome.x+=(side==='left'?1:-1)*.09;leg.footHome.z+=(side==='left'?1:-1)*.10}

 }
 makeBelt(){
  if(this.belt)return;const T=THREE,w=this.world;this.belt=new T.Group();this.pelvis.add(this.belt);this.belt.position.y=.12;
  const leather=w.mesh(new T.CylinderGeometry(.46,.46,.39,40,1,true),w.mat('#171412',{roughness:.82,side:T.DoubleSide}),this.belt);leather.scale.z=.72;
  const gold=w.mat('#dcb253',{metalness:.78,roughness:.28});
  const plate=w.mesh(new T.CylinderGeometry(.35,.35,.065,8),gold,this.belt);plate.rotation.x=Math.PI/2;plate.position.z=.35;plate.scale.x=1.08;
  const texture=new T.TextureLoader().load('/static/images/boxing/champion-belt.svg?v=1');texture.colorSpace=T.SRGBColorSpace;w.resources.push(texture);
  const face=w.mesh(new T.PlaneGeometry(1.65,.677),w.mat('#fff',{map:texture,transparent:true,metalness:.36,roughness:.4,side:T.DoubleSide}),this.belt);face.position.z=.391;
  for(const sign of [-1,1]){const side=w.mesh(new T.BoxGeometry(.22,.28,.045),gold,this.belt);side.position.set(sign*.40,0,.24);side.rotation.y=sign*.7}
  this.belt.visible=false;
 }
 presentation(state,dt){
  const T=THREE,kind=state.presentation,age=Math.max(0,(performance.now()-(state.presentationAt??performance.now()))/1000),smooth=(a,b,v)=>T.MathUtils.smoothstep(v,a,b);
  if(kind==='champion')this.makeBelt();if(this.belt)this.belt.visible=kind==='champion'&&age>=.7;
  this.canvas.dataset.presentation=kind||'fighting';
  if(!kind){this.downAmount=0;return;}
  this.gait=0;this.punchAt=-1000;
  let down=kind==='down'?smooth(0,.75,age):0;
  if(kind==='down'&&state.recoverAfter!=null)down*=1-smooth(state.recoverAfter-1.8,state.recoverAfter-.25,age);
  this.downAmount=down;
  const gettingUp=kind==='down'&&state.recoverAfter!=null?Math.sin(Math.PI*smooth(state.recoverAfter-1.8,state.recoverAfter-.25,age)):0;
  if(kind==='down')this.canvas.dataset.presentation=down>.95?'lying':age<1?'falling':down>.01?'rising':'ready';
  this.pelvis.rotation.set(.03*down,0,.035*down);this.spine.rotation.set(.04*down+.18*gettingUp,0,.05*down);this.chest.rotation.set(.06*down+.12*gettingUp,0,0);this.neck.rotation.set(.05*down,0,0);
  this.body.rotation.x=-Math.PI/2*down+.55*gettingUp;this.body.position.set(0,-.06+.23*down,0);
  const inv=this.pelvis.quaternion.clone().multiply(this.spine.quaternion).multiply(this.chest.quaternion).invert(),lift=kind==='champion'?smooth(.35,1.5,age):0;
  if(kind==='champion'){this.yaw+=Math.atan2(Math.sin(-this.yaw),Math.cos(-this.yaw))*(1-Math.exp(-dt*4));this.root.rotation.y=this.yaw}
  for(const [side,sign]of [['left',1],['right',-1]]){
   const arm=this.bones[side+'Arm'],u=new T.Vector3(sign*.25,-.5,.65).normalize().lerp(new T.Vector3(sign*.5,-.85,.08).normalize(),down),l=new T.Vector3(-sign*.15,.8,.4).normalize().lerp(new T.Vector3(-sign*.1,-.98,.06).normalize(),down);
   if(lift){u.lerp(new T.Vector3(sign*.65,.75,.1).normalize(),lift);l.lerp(new T.Vector3(sign*.05,.99,.1).normalize(),lift)}
   const uq=new T.Quaternion().setFromUnitVectors(arm.restUpper,u.normalize().applyQuaternion(inv)),lq=uq.clone().invert().multiply(new T.Quaternion().setFromUnitVectors(arm.restLower,l.normalize().applyQuaternion(inv)));
   arm.upper.position.copy(arm.cageBindPosition);arm.upper.quaternion.copy(uq);arm.lower.quaternion.copy(lq);arm.cageUpper.copy(uq);arm.cageLower.copy(lq);
   const leg=this.bones[side+'Leg'],sitU=new T.Vector3(sign*.12,-.98,.08).lerp(new T.Vector3(sign*.2,-.25,.95),gettingUp).normalize(),sitL=new T.Vector3(sign*.04,-.98,.15).lerp(new T.Vector3(sign*.06,-.98,.05),gettingUp).normalize(),lu=new T.Quaternion().setFromUnitVectors(leg.restUpper,sitU),ll=lu.clone().invert().multiply(new T.Quaternion().setFromUnitVectors(leg.restLower,sitL));
   lu.premultiply(this.pelvis.quaternion.clone().invert());leg.upper.quaternion.slerp(lu,down);leg.lower.quaternion.slerp(ll,down);
  }

  if(gettingUp>.001){this.body.updateMatrixWorld(true);const feet=['left','right'].map(side=>{const leg=this.bones[side+'Leg'];return leg.lower.localToWorld(leg.end.clone()).y});this.body.position.y+=(.07*this.height-Math.min(...feet))/this.root.scale.y*gettingUp}
 }
 relaxElbows(){for(const side of ['left','right']){const arm=this.bones[side+'Arm'];if(arm?.elbow)arm.elbow.quaternion.identity().slerp(arm.lower.quaternion,.5)}}
 supportLegs(dt){
  const T=THREE,s=this.supportSmooth,blend=s.confidence,targets={};this.root.updateMatrixWorld(true);
  for(const [side,sign]of [['left',1],['right',-1]]){
   const leg=this.bones[side+'Leg'],step=Math.sin(this.stepPhase||0)*sign,gait=(this.kickAmount>0?0:this.gait)||0,home=leg.footHome.clone();
   home.x+=sign*s.stance*.13*blend+step*(this.state.strafe||0)*.13*gait;
   home.z+=sign*s.stagger*.17*blend+step*(this.state.move||0)*.18*gait;
   home.y+=Math.max(0,step)*.13*gait;if(this.kickAmount>0&&this.punchHand===side){home.y+=this.kickAmount*1.65+this.kickExtension*1.60;home.z+=this.kickExtension*1.72;home.x+=sign*(this.kickAmount*.65-this.kickExtension*.82)}targets[side]=this.root.localToWorld(home);if(this.kickAmount>0&&this.punchHand===side){const from=leg.contactPrevious||leg.foot.getWorldPosition(new T.Vector3());for(const obstacle of this.kickObstacles||[]){const hit=BoxingContact.sweep(from,targets[side],obstacle,.11*this.height);if(hit)targets[side].copy(hit)}}
  }
  // Lower the pelvis enough for both fixed-length chains to reach their planted feet.
  let lower=0;for(const side of ['left','right']){const leg=this.bones[side+'Leg'],hip=leg.upper.getWorldPosition(new T.Vector3()),target=targets[side],length=(leg.lower.position.length()+leg.end.length())*this.root.scale.x-.008,horizontal=(hip.x-target.x)**2+(hip.z-target.z)**2;lower=Math.max(lower,hip.y-target.y-Math.sqrt(Math.max(.01,length*length-horizontal)))}
  this.body.position.y-=Math.max(0,lower)/this.root.scale.y;this.root.updateMatrixWorld(true);
  for(const [side,sign]of [['left',1],['right',-1]]){
   const b=this.bones[side+'Leg'],start=b.upper.getWorldPosition(new T.Vector3()),target=targets[side],l1=b.lower.position.length()*this.root.scale.x,l2=b.end.length()*this.root.scale.x,axis=target.clone().sub(start),distance=T.MathUtils.clamp(axis.length(),Math.abs(l1-l2)+.001,l1+l2-.001);axis.normalize();
   const along=(l1*l1-l2*l2+distance*distance)/(2*distance),height=Math.sqrt(Math.max(0,l1*l1-along*along)),pole=new T.Vector3(sign*(.12+(this.punchHand===side?this.kickAmount*.9:0)),this.punchHand===side?this.kickAmount*.45:0,1).applyQuaternion(this.root.quaternion);pole.addScaledVector(axis,-pole.dot(axis)).normalize();
   const knee=start.clone().addScaledVector(axis,along).addScaledVector(pole,height),end=start.clone().addScaledVector(axis,distance),inv=b.upper.parent.getWorldQuaternion(new T.Quaternion()).invert(),upper=knee.clone().sub(start).normalize().applyQuaternion(inv),lower=end.clone().sub(knee).normalize().applyQuaternion(inv),uq=new T.Quaternion().setFromUnitVectors(b.restUpper,upper);
   b.upper.quaternion.copy(uq);b.lower.quaternion.copy(uq.clone().invert().multiply(new T.Quaternion().setFromUnitVectors(b.restLower,lower)));this.root.updateMatrixWorld(true);
   const kickingFoot=this.kickAmount>0&&this.punchHand===side,pivot=this.computerMotion&&!kickingFoot?this.computerMotion.turn*(this.kickAmount>0?.8:.5):0;
   const footYaw=this.root.quaternion.clone().multiply(new T.Quaternion().setFromAxisAngle(new T.Vector3(0,1,0),pivot));
   if(kickingFoot){const forward=new T.Vector3(0,0,1).applyQuaternion(this.root.quaternion),shin=end.clone().sub(knee).normalize(),pointed=new T.Quaternion().setFromUnitVectors(forward,shin).multiply(this.root.quaternion);footYaw.slerp(pointed,this.kickExtension)}
   b.foot.quaternion.copy(b.lower.getWorldQuaternion(new T.Quaternion()).invert().multiply(footYaw));this.root.updateMatrixWorld(true);b.contactPrevious=b.foot.getWorldPosition(new T.Vector3());
  }
 }
 punch(hand,token,type='straight',age=0){if(this.punchToken===token)return;this.punchToken=token;this.punchHand=hand;this.punchType=type;this.punchAt=performance.now()-Math.max(0,age)}
 update(state,target,dt,time){
  if(!this.body)return;const T=THREE;this.state=state;this.target={x:state.x||0,z:state.z||0};const ease=1-Math.exp(-dt*15);this.position.lerp(new T.Vector2(this.target.x,this.target.z),ease);
  this.root.position.set(this.position.x,0,this.position.y);const yaw=state.presentation==='champion'?0:Math.atan2(target.x-this.position.x,target.z-this.position.y);this.yaw=(this.yaw??yaw)+Math.atan2(Math.sin(yaw-(this.yaw??yaw)),Math.cos(yaw-(this.yaw??yaw)))*ease;this.root.rotation.y=this.yaw;
  this.phase=time;this.body.rotation.set(0,0,0);const preview=this.workoutPreview;this.workoutPreview=true;super.restPose();this.workoutPreview=preview;for(const key of ['bend','slip','crouch'])this.poseSmooth[key]+=(Number(state[key]||0)-this.poseSmooth[key])*ease;
  for(const key of ['turn','hipTurn','tilt','headPitch','headYaw','headRoll'])this.poseSmooth[key]+=(Number(state.posture?.[key]||0)-this.poseSmooth[key])*ease;
  for(const key of Object.keys(this.supportSmooth))this.supportSmooth[key]+=(Number(state.lowerBody?.[key]||0)-this.supportSmooth[key])*ease;
  const support=this.supportSmooth,lowerMix=support.confidence,kneeDrop=(1-Math.cos((support.leftKnee+support.rightKnee)*.45))/.45;
  const computer=state.controlMode==='computer',elapsed=performance.now()-(this.punchAt??-1000),kicking=this.punchType==='kick';
  const motion=BoxingMotion.sample(this.punchType,this.punchHand,elapsed);motion.type=this.punchType;this.computerMotion=computer?motion:null;
  const pose={...this.poseSmooth,crouch:this.poseSmooth.crouch*(1-lowerMix)+Math.max(support.drop,kneeDrop)*lowerMix};
  if(computer){const dashAge=180-((state.dashVisualUntil||0)-performance.now()),duck=BoxingMotion.smooth(dashAge/35)*(1-BoxingMotion.smooth((dashAge-130)/90));pose.crouch=Math.max(.24+.48*duck,pose.crouch);if(duck>0)pose.bend=Math.max(.48*duck,pose.bend);pose.bend+=.18+motion.lean;pose.turn=motion.turn;pose.hipTurn=motion.hipTurn;pose.tilt+=motion.roll;pose.headYaw=-motion.turn*.48}
  const bow=Math.max(0,pose.bend),sway=Math.abs(pose.slip),envelope=computer?motion.reach:kicking?0:elapsed<0||elapsed>360?0:Math.sin(Math.PI*elapsed/360);
  this.kickAmount=computer&&kicking?motion.lift:0;this.kickExtension=computer&&kicking?motion.reach:0;
  const striking=state.arms?.[this.punchHand],alignment=striking?striking.upper.reduce((sum,v,i)=>sum+v*striking.lower[i],0):.7;
  let power=.16+.84*T.MathUtils.clamp((alignment-.15)/.85,0,1);if(this.punchType==='hook')power=Math.max(power,.55);if(this.punchType==='uppercut')power=Math.max(power,.45);
  const drive=envelope*(computer?1:power)*(kicking?.25:1),twist=(this.punchHand==='left'?1:-1)*(computer?-1:1)*drive;
  // Shoulder/hip rotation is continuous, including the wind-up before a strike event.
  const turn=pose.turn*1.05,hipYaw=pose.hipTurn*.82+twist*.08,remaining=turn-hipYaw,back=Math.min(0,pose.bend),pitch=pose.bend<0?pose.bend*.70:pose.bend,curve=1+Math.min(0,pose.bend)*1.1;
  this.pelvis.rotation.set(pitch*.32,hipYaw+twist*.04,-pose.slip*.16+support.hipRoll*.25*lowerMix+(computer?motion.roll*.4:0));
  this.spine.rotation.set(.06*curve+pitch*.43,remaining*.35+twist*.045,-pose.slip*.20+pose.tilt*.15);
  this.chest.rotation.set(.12*curve+pitch*.38+drive*(this.punchType==='uppercut'?-.04:.035),remaining*.65+twist*.065,-pose.slip*.22+pose.tilt*(computer?.65:.35));
  this.neck.rotation.set(-.08*curve-bow*.28+back*.08+pose.headPitch*.65,pose.headYaw*.75-twist*.04,pose.headRoll*.55-pose.tilt*.50+pose.slip*.58-support.hipRoll*.25*lowerMix);
  this.body.position.set(pose.slip*.17*(1-lowerMix)+support.shiftX*.30*lowerMix+twist*.025-(computer?motion.sign*motion.lift*.23:0),-.06-.48*pose.crouch-.08*bow-.045*sway,-bow*.12-back*.12+support.shiftZ*.26*lowerMix+drive*(computer?.12:.025)-this.kickAmount*.17);
  const shoulderFrame=new T.Quaternion().setFromAxisAngle(new T.Vector3(0,1,0),turn);
  const inverseTorso=this.pelvis.quaternion.clone().multiply(this.spine.quaternion).multiply(this.chest.quaternion).invert();
  const computerArms=computer?BoxingMotion.arms(motion,state.guard,state.guard_side||'both'):null;
  for(const side of ['left','right']){
   const b=this.bones[side+'Arm'],sign=side==='left'?1:-1,measured=computerArms?.[side]||state.arms?.[side];if(!b)continue;
   const upper=new T.Vector3(...(measured?.upper||[sign*.25,-.5,.65])).normalize(),lower=new T.Vector3(...(measured?.lower||[-sign*.15,.8,.4])).normalize();
   // Tracked elbows/wrists own the pose, even during a scoring event. No canned extension.
   const pull=Math.max(0,-upper.z);if(!computer){upper.applyQuaternion(shoulderFrame);lower.applyQuaternion(shoulderFrame)}upper.applyQuaternion(inverseTorso);lower.applyQuaternion(inverseTorso);
   b.upper.position.copy(b.cageBindPosition);b.upper.position.z+=(this.punchHand===side?.04:-.01)*drive-pull*.10;b.upper.position.x+=sign*pull*.025;
   b.upper.scale.setScalar(1);const uq=new T.Quaternion().setFromUnitVectors(b.restUpper,upper),lq=uq.clone().invert().multiply(new T.Quaternion().setFromUnitVectors(b.restLower,lower));
   b.cageUpper??=uq.clone();b.cageLower??=lq.clone();const armEase=1-Math.exp(-dt*32);
   b.cageUpper.slerp(uq,armEase);b.cageLower.slerp(lq,armEase);b.upper.quaternion.copy(b.cageUpper);b.lower.quaternion.copy(b.cageLower);
  }
  // Advance a shuffle cycle from actual displacement, so feet stop at cage/bag limits.
  const previous=this.previousStep,dx=previous?this.position.x-previous.x:0,dz=previous?this.position.y-previous.y:0;
  this.previousStep=this.position.clone();const speed=Math.min(3,Math.hypot(dx,dz)/Math.max(.001,dt));
  const requested=Math.hypot(state.move||0,state.strafe||0)>0;
  this.gait=(this.gait||0)+((requested?Math.min(1,speed/1.05):0)-(this.gait||0))*ease;
  this.stepPhase=(this.stepPhase||0)+speed*dt*9;
  const lateral=(state.strafe||0),forward=(state.move||0),phase=this.stepPhase,gait=this.gait;
  this.body.position.y+=Math.sin(phase*2)*.025*gait;
  for(const [side,sign]of [['left',1],['right',-1]]){
   const leg=this.bones[side+'Leg'];if(!leg)continue;leg.foot?.quaternion.identity();const step=Math.sin(phase)*sign,lift=Math.max(0,step);
   leg.upper.rotation.z=sign*.10+step*.26*lateral*gait;
   leg.upper.rotation.x=-.10+sign*.07-.7*pose.crouch-.13*bow+step*.32*forward*gait;
   leg.lower.rotation.x=.20+1.35*pose.crouch+.24*bow+.12*sway+lift*.48*gait;
   leg.upper.quaternion.premultiply(this.pelvis.quaternion.clone().invert());
  }
  if(!state.presentation)this.supportLegs(dt);
  this.presentation(state,dt);this.relaxElbows();
 }
};
window.BoxingWorld=class{
 constructor(container){
  const T=THREE;this.container=container;this.events=new AbortController();this.resources=[];this.actors=[];this.states=[];this.running=true;this.yaw=.28;this.elevation=.12;this.distance=3.15;this.mode='follow';this.focus=new T.Vector3(0,.9,0);this.last=performance.now();
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
  const T=THREE,canvas=document.createElement('canvas');canvas.width=canvas.height=1024;const c=canvas.getContext('2d');
  c.fillStyle='#b6c9c6';c.fillRect(0,0,1024,1024);
  for(let i=0;i<9000;i++){c.fillStyle=i%2?'#173d3509':'#ffffff18';c.fillRect((i*73)%1024,(i*137)%1024,2,2)}
  for(const [x,color]of [[0,'#365979'],[850,'#8d4847']]){c.fillStyle=color;c.fillRect(x,0,174,1024)}
  const octagon=(radius)=>{c.beginPath();for(let i=0;i<8;i++){const a=(i+.5)*Math.PI/4,x=512+Math.cos(a)*radius,y=512+Math.sin(a)*radius;i?c.lineTo(x,y):c.moveTo(x,y)}c.closePath()};
  octagon(469);c.strokeStyle='#eef0de';c.lineWidth=9;c.stroke();octagon(440);c.strokeStyle='#22403b44';c.lineWidth=2;c.stroke();
  c.beginPath();c.arc(512,512,227,0,Math.PI*2);c.fillStyle='#dce1cd';c.fill();c.strokeStyle='#193c35';c.lineWidth=3;c.stroke();
  c.textAlign='center';c.fillStyle='#173c35';c.font='italic 900 190px sans-serif';c.fillText('45',505,530);c.font='900 44px sans-serif';c.fillText('FIGHT CLUB',512,594);c.font='700 17px sans-serif';c.fillText('TRAINING  /  CHAMPIONSHIP',512,638);
  for(let i=0;i<4;i++){c.save();c.translate(512,512);c.rotate(i*Math.PI/2);c.fillStyle='#173c35';c.font='800 28px sans-serif';c.fillText('FORTY FIVE',0,-348);c.fillStyle='#eef0de';c.fillRect(-120,-325,240,3);c.restore()}
  const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;this.resources.push(texture);
  const floor=this.mesh(new T.CylinderGeometry(6,6,.22,8,1,false,Math.PI/8),this.mat('#ffffff',{map:texture,roughness:.92}));floor.position.y=-.12;floor.receiveShadow=true;
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
   const geom=new T.BufferGeometry();geom.setAttribute('position',new T.Float32BufferAttribute(lines,3));this.resources.push(geom);const material=new T.LineBasicMaterial({color:'#627786',transparent:true,opacity:.36});this.resources.push(material);group.add(new T.LineSegments(geom,material));
  }
  const skirt=this.mesh(new T.CylinderGeometry(6.05,6.15,.5,8,1,false,Math.PI/8),black);skirt.position.y=-.5;
  // A compact training hall replaces the placeholder spectators.
  const outer=this.mesh(new T.CylinderGeometry(11,11,.12,64),this.mat('#111c26',{roughness:.94}));outer.position.y=-.82;outer.receiveShadow=true;
  const warm=this.mat('#f0c47a',{emissive:'#dba851',emissiveIntensity:1.4}),cool=this.mat('#83b5d9',{emissive:'#5885aa',emissiveIntensity:1.2}),wall=this.mat('#152632',{roughness:.86});
  const sign=document.createElement('canvas');sign.width=1024;sign.height=512;const sc=sign.getContext('2d'),gradient=sc.createLinearGradient(0,0,1024,512);gradient.addColorStop(0,'#213d47');gradient.addColorStop(1,'#091721');sc.fillStyle=gradient;sc.fillRect(0,0,1024,512);sc.fillStyle='#d9b477';sc.fillRect(38,38,948,4);sc.fillRect(38,470,948,4);sc.textAlign='center';sc.fillStyle='#f4ead7';sc.font='italic 900 190px sans-serif';sc.fillText('45',512,255);sc.font='800 64px sans-serif';sc.fillText('FIGHT CLUB',512,345);sc.fillStyle='#90b9bc';sc.font='600 22px sans-serif';sc.fillText('THE TRAINING HALL',512,409);const signTexture=new T.CanvasTexture(sign);signTexture.colorSpace=T.SRGBColorSpace;this.resources.push(signTexture);const signMat=this.mat('#fff',{map:signTexture,emissive:'#284044',emissiveMap:signTexture,emissiveIntensity:.3});
  this.hallWalls=[];
  for(let i=0;i<8;i++){
   const a=i*Math.PI/4,normal=new T.Vector3(Math.cos(a),0,Math.sin(a)),group=new T.Group();this.scene.add(group);group.position.copy(normal).multiplyScalar(8.5);group.lookAt(0,0,0);this.hallWalls.push({group,mid:group.position.clone()});
   const panel=this.mesh(new T.BoxGeometry(6.7,3.7,.15),wall,group);panel.position.y=1.05;
   for(const x of [-2.8,2.8]){const rib=this.mesh(new T.BoxGeometry(.10,4.3,.20),metal,group);rib.position.set(x,1.3,.12);const strip=this.mesh(new T.BoxGeometry(.035,2.2,.025),i%2?cool:warm,group);strip.position.set(x,1.35,.235)}
   const screen=this.mesh(new T.PlaneGeometry(3.2,1.6),signMat,group);screen.position.set(0,1.6,.091);
   for(const y of [-.62,3.15]){const rail=this.mesh(new T.BoxGeometry(6.8,.06,.08),black,group);rail.position.set(0,y,.16)}
   const pa=normal.clone().multiplyScalar(5.7).setY(-.3),pb=new T.Vector3(Math.cos(a+Math.PI/4)*5.7,-.3,Math.sin(a+Math.PI/4)*5.7);this.bar(pa,pb,.018,i<4?warm:cool);
  }

  this.lamps=[];this.beams=[];for(let i=0;i<8;i++){const a=i*Math.PI/4;const lamp=this.mesh(new T.BoxGeometry(.7,.13,.25),this.mat('#ffffff',{emissive:i%2?'#85bfff':'#fff3df',emissiveIntensity:3}));lamp.position.set(Math.cos(a)*4,5.5,Math.sin(a)*4);this.lamps.push(lamp);const beam=this.mesh(new T.ConeGeometry(1.3,5,16,1,true),new T.MeshBasicMaterial({color:i%2?0xa1c9ff:0xffe7bd,transparent:true,opacity:.018,depthWrite:false,side:T.DoubleSide}));this.resources.push(beam.material);beam.position.set(Math.cos(a)*3.5,3.0,Math.sin(a)*3.5);this.beams.push(beam)}
  this.bag=new T.Group();this.scene.add(this.bag);const leather=this.mat('#243b43',{roughness:.48});const bagBody=this.mesh(new T.CylinderGeometry(.28,.30,1.25,24),leather,this.bag);bagBody.position.y=1.0;bagBody.castShadow=true;const trim=this.mat('#242c38');for(const y of [.43,1.57]){const band=this.mesh(new T.CylinderGeometry(.30,.30,.12,24),trim,this.bag);band.position.y=y}const label=document.createElement('canvas');label.width=256;label.height=256;const bc=label.getContext('2d');bc.fillStyle='#252b36';bc.fillRect(0,0,256,256);bc.strokeStyle='#dfb775';bc.lineWidth=8;bc.strokeRect(12,12,232,232);bc.fillStyle='#fff0cf';bc.textAlign='center';bc.font='bold 100px sans-serif';bc.fillText('45',128,125);bc.font='bold 34px sans-serif';bc.fillText('FIGHT CLUB',128,188);const bt=new T.CanvasTexture(label);bt.colorSpace=T.SRGBColorSpace;this.resources.push(bt);const badge=this.mesh(new T.PlaneGeometry(.30,.35),this.mat('#fff',{map:bt}),this.bag);badge.position.set(0,1.1,.301);this.bar(new T.Vector3(0,1.65,0),new T.Vector3(0,4.7,0),.018,metal,this.bag);const base=this.mesh(new T.CylinderGeometry(.52,.58,.12,24),black,this.bag);base.position.y=.06;
 }
 bind(){
  const signal=this.events.signal,points=new Map();let pinch=0;
  this.canvas.style.touchAction='none';this.canvas.addEventListener('pointerdown',e=>{if(this.cameraLocked)return;points.set(e.pointerId,{x:e.clientX,y:e.clientY});this.canvas.setPointerCapture(e.pointerId);if(points.size===2){const [a,b]=[...points.values()];pinch=Math.hypot(a.x-b.x,a.y-b.y)}},{signal});
  this.canvas.addEventListener('pointermove',e=>{if(this.cameraLocked)return;const old=points.get(e.pointerId);if(!old)return;const dx=e.clientX-old.x,dy=e.clientY-old.y;points.set(e.pointerId,{x:e.clientX,y:e.clientY});this.mode='orbit';if(points.size===2){const [a,b]=[...points.values()],d=Math.hypot(a.x-b.x,a.y-b.y);if(pinch)this.distance=THREE.MathUtils.clamp(this.distance*pinch/Math.max(1,d),2.4,14);pinch=d}else{this.yaw-=dx*.008;this.elevation=THREE.MathUtils.clamp(this.elevation+dy*.005,.12,1.1)}},{signal});
  for(const event of ['pointerup','pointercancel','lostpointercapture'])this.canvas.addEventListener(event,e=>{points.delete(e.pointerId);pinch=0},{signal});
  this.canvas.addEventListener('wheel',e=>{e.preventDefault();if(this.cameraLocked)return;this.distance=THREE.MathUtils.clamp(this.distance*Math.exp(e.deltaY*.001),2.4,14)},{signal,passive:false});
  this.canvas.addEventListener('keydown',e=>{if(this.cameraLocked)return;if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();this.mode='orbit';if(e.key==='ArrowLeft')this.yaw-=.12;if(e.key==='ArrowRight')this.yaw+=.12;if(e.key==='ArrowUp')this.distance=Math.max(2.4,this.distance-.3);if(e.key==='ArrowDown')this.distance=Math.min(14,this.distance+.3)}},{signal});
  this.canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();this.lost=true;this.notice.textContent=window.I18N?.lang==='en'?'Graphics interrupted; restoring…':'กราฟิกสะดุด กำลังกู้คืน…'},{signal});this.canvas.addEventListener('webglcontextrestored',()=>{this.lost=false;this.loading()},{signal});
 }
 view(mode){this.mode=mode;this.yaw=.28;this.elevation=mode==='top'?.95:mode==='follow'?.12:.22;this.distance=mode==='top'?9:mode==='follow'?3.15:4.2}
 add(model,id){const actor=new CageFighter(this,model,id);this.actors.push(actor);return actor}
 clearActors(){for(const a of this.actors)a.destroy();this.actors=[];this.states=[];this.loading()}
 loading(){const error=this.actors.some(a=>a.canvas.dataset.avatarState==='error'),pending=this.actors.some(a=>a.canvas.dataset.avatarState!=='ready');this.notice.textContent=error?(window.I18N?.lang==='en'?'Avatar unavailable. Leave and reopen the arena to retry.':'โหลดตัวละครไม่ได้ ออกแล้วเปิดสนามใหม่เพื่อลองอีกครั้ง'):pending?(window.I18N?.lang==='en'?'Loading your fighters…':'กำลังโหลดตัวละครของคุณ…'):''}
 set(states,practice=true){this.states=states;this.practice=practice;this.bag.visible=practice;const champion=states.findIndex(s=>s.presentation==='champion');if(champion>=0&&!this.celebrating){this.mode='champion';this.distance=3.8;this.elevation=.18}if(champion<0&&this.celebrating)this.view('follow');this.celebrating=champion>=0;this.loading()}
 hitBag(){this.bagHit=performance.now()}
 project(x,z,y=1.65){const v=new THREE.Vector3(x,y,z).project(this.camera);return{x:(v.x*.5+.5)*100,y:(-.5*v.y+.5)*100}}
 tick(now){
  if(!this.running)return;this.frame=requestAnimationFrame(t=>this.tick(t));const dt=Math.min(.05,(now-this.last)/1000);this.last=now;if(document.hidden||this.lost)return;
  const T=THREE,rect=this.canvas.getBoundingClientRect();if(rect.width<2||rect.height<2)return;const ratio=Math.min(devicePixelRatio||1,1.5);if(this.width!==rect.width||this.height!==rect.height){this.width=rect.width;this.height=rect.height;this.renderer.setPixelRatio(ratio);this.renderer.setSize(rect.width,rect.height,false);this.camera.aspect=rect.width/rect.height;this.camera.updateProjectionMatrix()}
  const states=this.states;for(let i=0;i<this.actors.length;i++){const state=states[i]||{},target=states[1-i]||{x:0,z:0};this.actors[i].update(state,target,dt,now/1000)}
  const ready=this.actors.filter(a=>a.body&&a.canvas.dataset.avatarState==='ready');for(const a of ready)a.root.updateMatrixWorld(true);
  // Both fighters see constraints from the same pose snapshot, independent of player order.
  const bodies=new Map(ready.map(a=>[a,BoxingContact.shapes(a)]));
  for(const actor of ready){const obstacles=ready.filter(a=>a!==actor).flatMap(a=>bodies.get(a));if(this.practice)obstacles.push({a:this.bag.localToWorld(new T.Vector3(0,.70,0)),b:this.bag.localToWorld(new T.Vector3(0,1.30,0)),radius:.30,kind:'bag'});actor.kickObstacles=obstacles;BoxingContact.constrain(actor,obstacles)}
  if(!this.cameraLocked){
  const down=states.some(s=>s.presentation==='down')&&!states.some(s=>s.presentation==='champion');
  let x=0,z=0;for(const s of states){x+=s.x||0;z+=s.z||0}const count=states.length||1,champion=this.mode==='champion'?this.actors[states.findIndex(s=>s.presentation==='champion')]:null;this.focus.lerp(new T.Vector3(champion?champion.position.x:states.length===1&&this.practice?x*.72:x/count,champion?1.02:down?.55:this.mode==='follow'?1.02:.9,champion?champion.position.y:states.length===1&&this.practice?z*.72:z/count),1-Math.exp(-dt*5));
  if(champion)this.yaw+=Math.atan2(Math.sin(-this.yaw),Math.cos(-this.yaw))*(1-Math.exp(-dt*3));
  if(this.mode==='side'&&states.length===2){const dx=states[1].x-states[0].x,dz=states[1].z-states[0].z,desired=Math.atan2(-dz,dx)+.18;this.yaw+=Math.atan2(Math.sin(desired-this.yaw),Math.cos(desired-this.yaw))*(1-Math.exp(-dt*3))}
  if(this.mode==='follow'&&this.actors[this.selfIndex||0]){const desired=this.actors[this.selfIndex||0].yaw+Math.PI+1.08;this.yaw+=Math.atan2(Math.sin(desired-this.yaw),Math.cos(desired-this.yaw))*(1-Math.exp(-dt*5))}
  const separation=states.length===2?Math.hypot(states[0].x-states[1].x,states[0].z-states[1].z):1;
  const radius=Math.max(down?4:this.distance,champion?0:this.mode==='follow'?separation*.8+1.8:separation*1.15+2.5)/Math.min(1,Math.max(.6,this.camera.aspect));const elevation=down?Math.max(.55,this.elevation):this.elevation;this.camera.position.set(this.focus.x+Math.sin(this.yaw)*radius*Math.cos(elevation),this.focus.y+Math.sin(elevation)*radius,this.focus.z+Math.cos(this.yaw)*radius*Math.cos(elevation));this.camera.lookAt(this.focus);
  }
  for(const f of this.fences){const towardCamera=f.mid.clone().sub(this.focus).dot(this.camera.position.clone().sub(this.focus));f.group.visible=towardCamera<4}
  for(const wall of this.hallWalls||[])wall.group.visible=wall.mid.clone().sub(this.focus).dot(this.camera.position.clone().sub(this.focus))<12;
  for(const lamp of this.lamps)lamp.visible=this.camera.position.y<5.3;for(const beam of this.beams)beam.visible=this.camera.position.y<5.3;
  const motion=!matchMedia('(prefers-reduced-motion: reduce)').matches&&document.body.dataset.effects!=='off';for(let i=0;i<this.beams.length;i++)this.beams[i].rotation.z=motion?Math.sin(now/2600+i)*.15:0;
  const elapsed=(now-(this.bagHit??-5000))/1000;this.bag.rotation.z=elapsed<2&&motion?Math.sin(elapsed*12)*Math.exp(-elapsed*3)*.12:0;
  this.renderer.render(this.scene,this.camera);
 }
 destroy(){this.running=false;cancelAnimationFrame(this.frame);this.events.abort();this.clearActors();for(const r of this.resources)r.dispose();this.renderer.dispose();this.renderer.forceContextLoss();this.container.replaceChildren()}
};
