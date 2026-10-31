/* Quaternius Universal Base Characters, CC0. See models/quaternius/LICENSE.txt.
   Shared saved avatar with authored skin weights for previews and live pose tracking. */
'use strict';
window.FitnessImportedAvatar=class extends FitnessCharacterRenderer {
 static cache=new Map();
 static asset(name){if(!this.cache.has(name))this.cache.set(name,fetch('/static/models/quaternius/'+name+'.json').then(r=>{if(!r.ok)throw Error('Avatar asset unavailable');return r.json()}).catch(e=>{this.cache.delete(name);throw e}));return this.cache.get(name)}
 status(state){
  this.canvas.dataset.avatarState=state;this.canvas.setAttribute('aria-busy',String(state==='loading'));
  this.statusNode?.remove();this.statusNode=null;
  if(state==='ready')return;
  const node=document.createElement('span');node.className='avatar-load-status';node.setAttribute('role','status');
  const en=window.I18N?.lang==='en';node.textContent=state==='loading'?(en?'Loading avatar…':'กำลังโหลดตัวละคร…'):(en?'Avatar could not load':'โหลดตัวละครไม่ได้');
  if(state==='error'){const retry=document.createElement('button');retry.type='button';retry.textContent=en?'Retry':'ลองอีกครั้ง';retry.onclick=()=>this.set(this.model);node.append(' ',retry)}
  this.canvas.after(node);this.statusNode=node;
 }
 set(model){
  if(this.destroyed)return;this.model=model;
  if(this.fallback){this.status('error');return}
  const gender=model.appearance?.gender==='female'?'female':'male';
  // Invalidate every older request, even when returning to an already loaded gender.
  const serial=this.loadSerial=(this.loadSerial||0)+1;
  if(this.loadedGender===gender&&this.assetBody){this.build();this.status('ready');this.draw();return}
  this.status('loading');
  // A neutral loading state replaces the old procedural preview entirely.
  if(!this.body){this.gpu.setClearColor(0x000000,0);this.gpu.clear()}
  Promise.all([FitnessImportedAvatar.asset(gender),FitnessImportedAvatar.asset(gender+'-rig'),...['Hair_Buzzed','Hair_SimpleParted','Hair_Long'].map(n=>FitnessImportedAvatar.asset(n)),this.loadTextures(gender)]).then(([body,rig,...parts])=>{
   if(this.destroyed||serial!==this.loadSerial)return;
   this.assetBody=body;this.assetRig=rig;this.assetHair=parts.slice(0,3);this.loadedGender=gender;this.build();this.status('ready');this.draw();
  }).catch(()=>{if(!this.destroyed&&serial===this.loadSerial)this.status('error')});
 }
 start(){if(this.statusNode&&!this.statusNode.isConnected)this.canvas.after(this.statusNode);super.start()}
 draw(){if(this.body&&!this.fallback)super.draw()}
 tint(color,base){const b=new THREE.Color(base);color.r/=b.r;color.g/=b.g;color.b/=b.b;}
 loadTextures(gender){
  this.textures??={};this.textureLoads??={};
  const names=[gender+'-color.jpg',gender+'-normal.png','hair-color.png','hair-normal.png','hair2-color.png','hair2-normal.png','eyes-color.jpg'];
  return Promise.all(names.map(name=>this.textureLoads[name]??=(new Promise((resolve,reject)=>new THREE.TextureLoader().load('/static/models/quaternius/'+name,t=>{if(this.destroyed){t.dispose();resolve();return}if(name.includes('color'))t.colorSpace=THREE.SRGBColorSpace;t.flipY=true;this.textures[name]=t;resolve(t)},undefined,error=>{delete this.textureLoads[name];reject(error)})))));
 }
 build(){
  if(!this.assetBody)return;
  this.clear();const T=THREE,a=this.model.appearance||{},v=this.model.visual||{},gender=this.loadedGender;
  this.height=v.height_scale||1;this.body=new T.Group();this.root.add(this.body);
  const bodyData=this.assetBody.find(m=>m.name.includes('Super'));
  const maxY=Math.max(...bodyData.position.filter((_,i)=>i%3===1));const unit=3.7/maxY;
  const development=FitnessMuscleProgression.development(this.model.growth);
  const full=Math.max(0,Math.min(1,v.fullness??.25));
  const skin=this.material(a.skin_color||'#d79f7a',.78);this.tint(skin.color,'#d8aa87');skin.map=this.textures[gender+'-color.jpg'];skin.normalMap=this.textures[gender+'-normal.png'];skin.normalScale.set(.65-full*.35,.65-full*.35);
  skin.onBeforeCompile=shader=>{
   shader.vertexShader='attribute float muscleDevelopment; varying float vMuscleDevelopment;\n'+shader.vertexShader;
   shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\n vMuscleDevelopment=muscleDevelopment;');
   shader.fragmentShader='varying float vMuscleDevelopment;\n'+shader.fragmentShader;
   shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>',`#ifdef USE_MAP
    vec4 authored=texture2D(map,vMapUv);
    vec4 quiet=texture2D(map,vMapUv,5.0);
    diffuseColor*=mix(quiet,authored,vMuscleDevelopment);
   #endif`);
   shader.fragmentShader=shader.fragmentShader.replace('#include <normal_fragment_maps>',`vec3 untrainedNormal=normal;
    #include <normal_fragment_maps>
    normal=normalize(mix(untrainedNormal,normal,vMuscleDevelopment));`);
  };
  skin.customProgramCacheKey=()=> 'quaternius-muscle-progression-v1';
  const hair=this.material(a.hair_color||'#302333',.85);hair.map=this.textures['hair-color.png'];hair.normalMap=this.textures['hair-normal.png'];hair.side=T.DoubleSide;hair.alphaTest=.35;
  const hair2=hair.clone();hair2.map=this.textures['hair2-color.png'];hair2.normalMap=this.textures['hair2-normal.png'];this.resources.push(hair2);
  const eyes=this.material('#ffffff',.4);eyes.map=this.textures['eyes-color.jpg'];
  const eyeTint=new T.Color(a.eye_color||'#553521');this.tint(eyeTint,'#553521');
  eyes.onBeforeCompile=shader=>{shader.uniforms.eyeTint={value:eyeTint};shader.fragmentShader='uniform vec3 eyeTint;\n'+shader.fragmentShader;shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>',`#include <map_fragment>
   float saturation = max(diffuseColor.r,max(diffuseColor.g,diffuseColor.b))-min(diffuseColor.r,min(diffuseColor.g,diffuseColor.b));
   diffuseColor.rgb *= mix(vec3(1.0),eyeTint,smoothstep(0.03,0.12,saturation));`)};
  eyes.customProgramCacheKey=()=> 'quaternius-iris-tint-v1';
  const top=this.material(a.top_color||'#284b73',.95),shorts=this.material(a.shorts_color||'#172d4c',.95);top.side=shorts.side=T.DoubleSide;
  const deform=(x,y,z)=>{
   [x,y,z]=FitnessMuscleProgression.deform(x,y,z,maxY,development).position;
   const h=y/maxY;const torso=Math.exp(-Math.pow((h-.60)/.15,2));const head=h>.86;
   // Profile-driven approximate fullness; weight never estimates muscle mass.
   x*=1+full*(head?.08:.15+.40*torso);z*=1+full*(head?.08:.18+.65*torso);
   if(head){const jaw=Math.exp(-Math.pow((h-.89)/.025,2));x*=1+(a.face==='angular'?.06:-.025)*jaw;
    if(z>.075&&Math.abs(x)<.035){const nose=Math.exp(-Math.pow((h-.934)/.016,2));x*=1+(a.nose==='broad'?.32:a.nose==='rounded'?.12:0)*nose;z+=(a.nose==='rounded'?.004:0)*nose;}
    if(Math.abs(x)>.018&&Math.abs(x)<.065&&z>.05){const eye=Math.exp(-Math.pow((h-.938)/.012,2));y+=(y-maxY*.938)*(a.eyes==='round'?.20:a.eyes==='narrow'?-.20:0)*eye;}
   }
   return [x*unit,y*unit,z*unit];
  };
  this.buildRig(deform);
  const make=(data,mat,index=data.index,offset=0,skin=this.assetRig.meshes[data.name]?.skin)=>{
   const vertices=[];for(let i=0;i<data.position.length;i+=3){const p=deform(...data.position.slice(i,i+3));for(let k=0;k<3;k++)vertices.push(p[k]+offset*data.normal[i+k])}
   const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(vertices,3));geo.setAttribute('uv',new T.Float32BufferAttribute(data.uv,2));geo.setAttribute('muscleDevelopment',new T.Float32BufferAttribute(data.position.filter((_,i)=>i%3===0).map((_,i)=>FitnessMuscleProgression.deform(...data.position.slice(i*3,i*3+3),maxY,development).detail),1));geo.setIndex(index);if(offset)geo.setAttribute('normal',new T.Float32BufferAttribute(data.normal,3));else geo.computeVertexNormals();if(!skin)return this.mesh(geo,mat,this.body);
   geo.setAttribute('skinIndex',new T.Uint16BufferAttribute(skin.index,4));geo.setAttribute('skinWeight',new T.Float32BufferAttribute(skin.weight,4));
   const mesh=new T.SkinnedMesh(geo,mat);mesh.frustumCulled=false;this.resources.push(geo);this.body.add(mesh);mesh.bind(this.skeleton);return mesh;
  };
  for(const data of this.assetBody){make(data,data.name.includes('Super')?skin:data.name==='Eyes'?eyes:hair);
   if(data.name.includes('Super')){make(data.clothing.shorts,shorts,data.clothing.shorts.index,.018,this.assetRig.meshes[data.name].clothing.shorts);const style=a.clothing==='tee'?'tee':a.clothing==='tank'?'tank':gender==='female'?'sports':null;if(style)make(data.clothing[style],top,data.clothing[style].index,.022,this.assetRig.meshes[data.name].clothing[style])}
  }
  const style=a.hair||'short',hairIndex={short:0,swept:1,bob:2,ponytail:0,curly:0}[style];
  if(hairIndex!==undefined)for(const data of this.assetHair[hairIndex]){
   const mesh=make(data,data.material==='MI_Hair_2'?hair2:hair);mesh.position.y=(gender==='female'&&hairIndex<2?-.043:gender==='male'&&hairIndex===2?.043:0)*unit;
  }
  const plainHair=this.material(a.hair_color||'#302333',.9);
  if(style==='curly')for(let i=0;i<60;i++){const theta=i*2.39996,r=.088*Math.sqrt(i/60),x=Math.cos(theta)*r,z=Math.sin(theta)*r;this.ell(x*unit,(maxY-.016+.043*Math.sqrt(1-r*r/.008))*unit,(z-.012)*unit,.018*unit,.022*unit,.018*unit,plainHair,this.body)}
  if(style==='ponytail'){this.ell(0,(maxY-.08)*unit,-.10*unit,.037*unit,.05*unit,.04*unit,plainHair,this.body);this.ell(0,(maxY-.20)*unit,-.12*unit,.035*unit,.13*unit,.036*unit,plainHair,this.body)}
  if(this.workoutPreview||this.dumbbells)this.addDumbbells();
  this.root.scale.setScalar(this.height);this.restPose();
 }

 // The bind pose and weights come from the approved CC0 model, not a replacement mesh.
 buildRig(deform){
  const T=THREE,base=new T.Bone(),bones=[base];this.body.add(base);this.rigged=true;
  for(const side of ['left','right'])for(const kind of ['Arm','Leg']){
   const points=this.assetRig.joints[side+kind].map(p=>new T.Vector3(...deform(...p))),[shoulder,elbow,wrist]=points;
   const upper=new T.Bone(),lower=new T.Bone();upper.position.copy(shoulder);lower.position.copy(elbow).sub(shoulder);base.add(upper);upper.add(lower);bones.push(upper,lower);
   this.bones[side+kind]={upper,lower,restUpper:elbow.clone().sub(shoulder).normalize(),restLower:wrist.clone().sub(elbow).normalize(),end:wrist.clone().sub(elbow)};
  }
  this.fingers=[];const byName={hand_l:this.bones.leftArm.lower,hand_r:this.bones.rightArm.lower};
  for(const data of this.assetRig.fingers){
   const bone=new T.Bone(),parent=byName[data.parent],world=new T.Vector3(...deform(...data.position));
   // Positions here are in body bind coordinates, independent of profile root scaling.
   const parentBind=data.parent.startsWith('hand_')?this.assetRig.joints[data.parent.endsWith('_l')?'leftArm':'rightArm'][1]:this.assetRig.fingers.find(f=>f.name===data.parent).position;
   bone.position.copy(world).sub(new T.Vector3(...deform(...parentBind)));parent.add(bone);byName[data.name]=bone;bones.push(bone);this.fingers.push({bone,name:data.name});
  }
  this.handGrips={};
  for(const side of ['left','right']){
   const suffix=side==='left'?'l':'r',sign=side==='left'?1:-1;
   const point=name=>new T.Vector3(...deform(...this.assetRig.fingers.find(f=>f.name===name+'_'+suffix).position));
   const roots=['index','middle','ring','pinky'].map(n=>point(n+'_01'));
   const center=roots.reduce((sum,p)=>sum.add(p),new T.Vector3()).multiplyScalar(.25);
   const across=roots[0].clone().sub(roots[3]).normalize(),down=point('middle_02').sub(roots[1]).normalize();
   const inward=new T.Vector3(-sign,0,0).addScaledVector(down,sign*down.x).normalize();
   center.addScaledVector(inward,.052);
   this.handGrips[side]={center,across,axis:new T.Vector3().crossVectors(down,inward).normalize()};
  }
  this.body.updateMatrixWorld(true);this.skeleton=new T.Skeleton(bones);this.resources.push(this.skeleton);
 }
 restPose(){
  if(!this.rigged)return super.restPose();
  for(const b of Object.values(this.bones)){b.upper.quaternion.identity();b.lower.quaternion.identity()}
  for(const {bone,name}of this.fingers||[]){
   bone.quaternion.identity();if(!(this.workoutPreview||this.dumbbells)||name.includes('leaf'))continue;
   const hand=this.handGrips[name.endsWith('_l')?'left':'right'];
   if(name.startsWith('thumb')){
    if(name.includes('_01_')){
     const root=this.assetRig.fingers.find(f=>f.name===name),next=this.assetRig.fingers.find(f=>f.parent===name);
     const rest=new THREE.Vector3(...next.position).sub(new THREE.Vector3(...root.position)).normalize();
     // Oppose the thumb across the palm rather than spreading it away from the handle.
     const target=hand.across.clone().multiplyScalar(-.7).add(new THREE.Vector3(0,-.7,0)).normalize();
     bone.quaternion.setFromUnitVectors(rest,target);
    }else bone.quaternion.setFromAxisAngle(hand.axis,.55);
   }else bone.quaternion.setFromAxisAngle(hand.axis,name.includes('_01_')?1.25:name.includes('_02_')?1.4:1.0);
  }
  if(this.workoutPreview&&!this.livePose){
   const curl=this.motion?.matches?1.1:.25+(1+Math.sin(this.phase*1.7))*.95;
   for(const side of ['left','right'])this.bones[side+'Arm']?.lower.quaternion.setFromAxisAngle(new THREE.Vector3(-1,0,0),curl);
  }
 }
 applyPose(live,inverse){
  if(!this.rigged)return super.applyPose(live,inverse);
  for(const [kind,group]of [['Arm','arms'],['Leg','legs']])for(const side of ['left','right']){
   const b=this.bones[side+kind],p=live[group]?.[side];if(!b||!p)continue;
   const upper=new THREE.Vector3(...p.upper).applyQuaternion(inverse).normalize(),lower=new THREE.Vector3(...p.lower).applyQuaternion(inverse).normalize();
   b.upper.quaternion.setFromUnitVectors(b.restUpper,upper);
   b.lower.quaternion.copy(b.upper.quaternion).invert().multiply(new THREE.Quaternion().setFromUnitVectors(b.restLower,lower));
  }
 }
 poseBounds(){
  if(!this.rigged)return super.poseBounds();
  // Joint endpoints give stable framing without reading every skinned vertex each frame.
  this.root.updateMatrixWorld(true);const box=new THREE.Box3();
  for(const b of Object.values(this.bones))for(const p of [b.upper.getWorldPosition(new THREE.Vector3()),b.lower.getWorldPosition(new THREE.Vector3()),b.lower.localToWorld(b.end.clone())])box.expandByPoint(p);
  for(const x of [-.4,.4])for(const y of [1.5,3.8])box.expandByPoint(this.body.localToWorld(new THREE.Vector3(x,y,0)));
  return box.expandByScalar(.3*this.height);
 }
 setDumbbells(enabled){this.dumbbells=!!enabled;if(this.assetBody){this.build();this.draw()}}
 setWorkoutPreview(enabled){this.workoutPreview=!!enabled;if(this.assetBody){this.build();this.draw()}}
 addDumbbells(){
  const T=THREE,metal=this.material('#aebac8',.28),plate=this.material('#253140',.65);
  for(const side of ['left','right']){
   const b=this.bones[side+'Arm'],hand=this.handGrips[side],grip=new T.Group();grip.name='preview-dumbbell';grip.position.copy(hand.center).sub(b.upper.position).sub(b.lower.position);grip.quaternion.setFromUnitVectors(new T.Vector3(1,0,0),hand.across);b.lower.add(grip);
   const bar=this.mesh(new T.CylinderGeometry(.035,.035,.48,12),metal,grip);bar.rotation.z=Math.PI/2;
   for(const x of [-.21,.21]){const weight=this.mesh(new T.CylinderGeometry(.115,.115,.10,12),plate,grip);weight.rotation.z=Math.PI/2;weight.position.x=x}
  }
 }
 destroy(){this.statusNode?.remove();super.destroy();for(const texture of Object.values(this.textures||{}))texture.dispose();this.loadSerial=(this.loadSerial||0)+1}
};
