/* 45 Fitness Coach V44. Original procedural 3D character; Three.js MIT.
   Smooth anatomical silhouettes, custom face, articulated live pose. No remote assets. */
'use strict';
window.FitnessCharacterRenderer=class {
 constructor(canvas){
  this.canvas=canvas;this.yaw=-.28;this.phase=0;this.running=false;this.events=new AbortController();this.resources=[];this.bones={};this.frame=null;this.inView=true;
  const T=window.THREE;
  try{if(!T)throw Error('3D engine unavailable');this.gpu=new T.WebGLRenderer({canvas,alpha:true,antialias:true,powerPreference:'low-power'});}catch(e){this.fallback=new FitnessBlockFallback(canvas);canvas.dataset.renderer='fallback';canvas.setAttribute('aria-label','โหมดภาพสำรอง — อุปกรณ์นี้เปิด WebGL ไม่ได้');return;}
  canvas.dataset.renderer='webgl';this.gpu.setPixelRatio(Math.min(window.devicePixelRatio||1,2));this.gpu.outputColorSpace=T.SRGBColorSpace;this.gpu.toneMapping=T.ACESFilmicToneMapping;this.gpu.toneMappingExposure=1.15;
  this.scene=new T.Scene();this.camera=new T.PerspectiveCamera(31,1,.05,50);this.scene.add(new T.HemisphereLight(0xe7efff,0x67566b,2.2));
  for(const [color,intensity,x,y,z]of [[0xffdfc0,3.8,-3,6,5],[0xb4c8ff,2.2,3,3,-3],[0xffffff,.7,2,2,5]]){const l=new T.DirectionalLight(color,intensity);l.position.set(x,y,z);this.scene.add(l)}
  this.root=new T.Group();this.scene.add(this.root);this.lastTime=0;
  canvas.style.touchAction='pan-y';canvas.tabIndex=0;
  canvas.addEventListener('pointerdown',e=>{this.drag={x:e.clientX,yaw:this.yaw};canvas.setPointerCapture?.(e.pointerId)},{signal:this.events.signal});
  canvas.addEventListener('pointermove',e=>{if(this.drag){this.yaw=this.drag.yaw+(e.clientX-this.drag.x)*.012;this.draw()}},{signal:this.events.signal});
  for(const event of ['pointerup','pointercancel'])canvas.addEventListener(event,()=>this.drag=null,{signal:this.events.signal});
  canvas.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();this.rotate(e.key==='ArrowLeft'?-.15:.15)}},{signal:this.events.signal});
  this.visibility=()=>{if(document.hidden)this.cancel();else this.schedule()};document.addEventListener('visibilitychange',this.visibility,{signal:this.events.signal});
  this.observer=new IntersectionObserver(entries=>{this.inView=entries[0].isIntersecting;this.inView?this.schedule():this.cancel()});this.observer.observe(canvas);
  this.motion=matchMedia('(prefers-reduced-motion: reduce)');this.resize=new ResizeObserver(()=>this.draw());this.resize.observe(canvas);
 }
 set(model){this.model=model;if(this.fallback)return this.fallback.set(model);this.build();this.draw()}
 material(color,roughness=.62){const m=new THREE.MeshStandardMaterial({color,roughness,metalness:0});this.resources.push(m);return m}
 mesh(geometry,material,parent=this.root){this.resources.push(geometry);const m=new THREE.Mesh(geometry,material);parent.add(m);return m}
 ell(x,y,z,rx,ry,rz,mat,parent=this.root){const m=this.mesh(new THREE.SphereGeometry(1,24,16),mat,parent);m.position.set(x,y,z);m.scale.set(rx,ry,rz);return m}
 tube(points,radius,mat,parent=this.root){return this.mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p))),20,radius,7,false),mat,parent)}
 surface(rings,mat,parent=this.root){
  const n=48,vertices=[],indices=[];
  // Interpolated longitudinal contours keep cheeks and limbs smooth.
  const original=rings,smooth=[];
  for(let i=0;i<original.length-1;i++)for(let j=0;j<4;j++){
   const t=j/4,p0=original[Math.max(0,i-1)],p1=original[i],p2=original[i+1],p3=original[Math.min(original.length-1,i+2)];
   smooth.push(Array.from({length:4},(_,k)=>{const a=p0[k]||0,b=p1[k]||0,c=p2[k]||0,d=p3[k]||0;const v=.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t);return k===1||k===2?Math.max(.001,v):v}));
  }smooth.push(original[original.length-1]);rings=smooth;
  // rings: y, half width, half depth, z offset. Smooth normals for a continuous silhouette.
  for(const [y,w,d,z=0]of rings)for(let i=0;i<=n;i++){const a=i/n*Math.PI*2;vertices.push(Math.cos(a)*w,y,Math.sin(a)*d+z)}
  for(let j=0;j<rings.length-1;j++)for(let i=0;i<n;i++){const a=j*(n+1)+i,b=a+n+1;indices.push(a,b,a+1,b,b+1,a+1)}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));if(rings[1][0]<rings[0][0])for(let i=0;i<indices.length;i+=3)[indices[i+1],indices[i+2]]=[indices[i+2],indices[i+1]];g.setIndex(indices);g.computeVertexNormals();return this.mesh(g,mat,parent);
 }
 clear(){for(const r of this.resources)r.dispose();this.resources=[];this.root.clear();this.bones={}}
 build(){
  this.clear();const T=THREE,a=this.model.appearance||{},v=this.model.visual||{},g=this.model.growth?.levels||{};
  const full=Math.max(0,Math.min(1,v.fullness??.25)),muscle=Math.max(0,Math.min(1,a.build??.45));
  const growth=k=>Math.min(.12,(g[k]||0)*.12),female=a.gender==='female';
  this.height=v.height_scale||1;
  const skin=this.material(a.skin_color||'#d79f7a'),lip=this.material('#a45b50'),hair=this.material(a.hair_color||'#302333',.85),cloth=this.material(a.shorts_color||'#172d4c',.9),trim=this.material('#839bb6'),white=this.material('#fff5e5',.3),iris=this.material(a.eye_color||'#553521',.35),black=this.material('#15101c',.25),glint=this.material('#ffffff',.15);
  this.body=new T.Group();this.root.add(this.body);
  const body=this.body,waist=(female?.27:.29)+full*.20,shoulder=(female?.41:.44)+muscle*.11+growth('shoulders'),chest=(female?.37:.36)+muscle*.12+growth('chest'),belly=.19+full*.19;
  this.surface([[1.65,.24,.15],[1.72,.33+full*.07,.20],[1.92,waist,belly],[2.13,waist*.96,belly*1.04,.018*full],[2.35,chest*.96,.22+full*.09],[2.56,chest,.235+muscle*.04+full*.05],[2.72,shoulder,.20],[2.82,.37+muscle*.05,.16],[2.91,.16,.13],[3.06,.125,.12]],skin,body);
  // Pectoral and clavicle surfaces; restrained with fuller body types.
  if(full<.75)for(const sign of [-1,1]){const p=this.ell(sign*chest*.46,2.55,.16,.20+muscle*.035,.125,.045*(1-full*.5),skin,body);p.rotation.z=sign*.06;}
  if(muscle>.55&&full<.36)for(let i=0;i<3;i++)for(const sign of [-1,1])this.ell(sign*.095,2.30-i*.15,.19,.085,.075,.04*(1-full),skin,body);
  // Tailored sportswear, with a covered sports top for female characters.
  const top=this.material(a.top_color||'#284b73',.9);
  if(a.clothing==='tank'||a.clothing==='tee'){
   this.surface([[1.88,waist+.025,belly+.03],[2.13,waist+.03,belly*1.04+.03],[2.55,chest+.025,.29+full*.05],[2.73,shoulder+.02,.23],[2.84,.18,.15]],top,body);
  }else if(female){
   this.surface([[2.36,chest+.02,.25+full*.09],[2.57,chest+.025,.29+full*.05],[2.68,chest*.94,.25]],top,body);
   for(const sign of [-1,1])this.tube([[sign*.24,2.57,.25],[sign*.25,2.81,.12],[sign*.25,2.65,-.21]],.035,top,body);
  }
  // Fitted shorts and waistband.
  this.surface([[1.47,.39+full*.09,.265],[1.60,.41+full*.09,.28],[1.74,.39+full*.10,.27],[1.86,waist+.018,belly+.015]],cloth,body);
  this.surface([[1.82,waist+.021,belly+.018],[1.88,waist+.021,belly+.018]],trim,body);
  for(const sign of [-1,1])this.tube([[sign*.04,1.85,belly+.025],[sign*.02,1.78,belly+.032],[sign*.045,1.71,belly+.035]],.009,trim,body);
  this.hipY=1.7;this.shoulderY=2.76;
  for(const [side,sign]of [['right',-1],['left',1]]){
   const upper=new T.Group(),lower=new T.Group();upper.position.set(sign*(shoulder+.035),2.76,0);body.add(upper);upper.add(lower);lower.position.y=-.53;
   this.bones[side+'Arm']={upper,lower,length:.53};
   if(a.clothing==='tee')this.surface([[.02,.19,.20],[-.25,.19,.19]],top,upper);
   const ar=.135+muscle*.045+full*.035+growth('arms')*.30;
   this.ell(0,-.055,0,ar*1.15,.20,ar*1.12,skin,upper);
   this.surface([[0,ar*.75,ar*.82],[-.16,ar,ar*1.07],[-.32,ar*.88,ar*.94],[-.49,.09+full*.02,.10]],skin,upper);
   this.ell(0,0,0,.10,.105,.10,skin,lower);
   this.surface([[0,.095,.10],[-.12,ar*.84,ar*.87],[-.31,.09+full*.015,.085],[-.48,.067,.066]],skin,lower);
   this.ell(0,-.55,.015,.086,.12,.049,skin,lower);
   for(let i=0;i<4;i++){const x=(i-1.5)*.041,y=-.66+(i===0||i===3?.02:0);this.ell(x,y,.024,.021,.085,.022,skin,lower);this.ell(x,y-.07,.031,.020,.040,.022,skin,lower)}
   const thumb=this.ell(-sign*.088,-.56,.045,.028,.088,.030,skin,lower);thumb.rotation.z=sign*.5;
   const thigh=new T.Group(),shin=new T.Group();thigh.position.set(sign*(.18+full*.025),1.70,0);body.add(thigh);thigh.add(shin);shin.position.y=-.73;this.bones[side+'Leg']={upper:thigh,lower:shin,length:.73};
   const lr=.155+full*.055+muscle*.025+growth('legs')*.25;
   this.surface([[.04,lr*1.05,lr*1.12],[-.20,lr,lr*1.07],[-.47,lr*.80,lr*.88],[-.70,.10+full*.02,.115]],skin,thigh);
   this.surface([[0,lr*1.10,lr*1.16],[-.31,lr*1.07,lr*1.12]],cloth,thigh);
   this.surface([[-.29,lr*1.08,lr*1.13],[-.33,lr*1.08,lr*1.13]],trim,thigh);
   this.ell(0,0,.025,.108+full*.02,.12,.105,skin,shin);
   this.surface([[0,.10,.105],[-.18,.115+muscle*.025+full*.025,.135],[-.39,.09+full*.02,.10],[-.66,.065,.072]],skin,shin);
   this.ell(0,-.71,.10,.092,.075,.185,skin,shin);
   for(let i=0;i<5;i++)this.ell((i-2)*.032,-.73,.255-Math.abs(i-1)*.012,.020,.035,.05,skin,shin);
  }
  const head=new T.Group();head.position.y=3.06;body.add(head);this.head=head;
  const angular=a.face==='angular',hw=(angular?.30:.315)+full*.035;
  this.surface([[0,.13,.12,.01],[.045,.21,.18,.018],[.13,angular?.26:hw*.88,.225,.012],[.25,hw,.255],[.40,hw*1.03,.25],[.57,hw*.94,.225,-.015],[.69,hw*.69,.18,-.02],[.735,.06,.04,-.02]],skin,head);
  for(const sign of [-1,1]){
   this.ell(sign*(hw+.018),.32,-.015,.069,.105,.055,skin,head);
   this.ell(sign*(hw+.043),.32,.019,.028,.059,.025,lip,head);
   const eyeY=.40,eyeX=sign*.133,eh=a.eyes==='round'?.065:a.eyes==='narrow'?.039:.051;
   this.ell(eyeX,eyeY,.231,.100,eh+.020,.040,skin,head);
   this.ell(eyeX,eyeY,.258,.083,eh,.033,white,head);
   this.ell(eyeX,eyeY,.286,.037,eh*.83,.015,iris,head);
   this.ell(eyeX,eyeY,.299,.018,eh*.53,.006,black,head);
   this.ell(eyeX-.010,eyeY+.016,.305,.008,.010,.003,glint,head);
   this.tube([[eyeX-.085,eyeY+.015,.264],[eyeX-.048,eyeY+eh,.278],[eyeX+.025,eyeY+eh*.96,.280],[eyeX+.08,eyeY+.01,.261]],.009,skin,head);
   this.tube([[eyeX-.086,.512,.231],[eyeX-.028,.532,.246],[eyeX+.030,.527,.245],[eyeX+.081,.505,.230]],.015,hair,head);
  }
  const nose=a.nose||'straight',nw=nose==='broad'?.072:nose==='rounded'?.056:.040;
  this.ell(0,.348,.258,nw*.65,.105,.055,skin,head);this.ell(0,.285,.299,nw,.047,nose==='straight'?.069:.056,skin,head);
  for(const sign of [-1,1]){this.ell(sign*nw*.70,.270,.292,nw*.47,.027,.036,skin,head);this.ell(sign*nw*.65,.253,.306,.012,.009,.010,lip,head)}
  this.tube([[-.105,.166,.223],[-.047,.177,.249],[0,.172,.257],[.047,.177,.249],[.105,.168,.224]],.012,lip,head);
  this.tube([[-.082,.159,.232],[0,.149,.252],[.080,.160,.232]],.009,skin,head);
  this.ell(0,.095,.191,.12,.041,.037,skin,head);
  const style=a.hair||'short';
  if(style!=='bald'){
   const cap=this.mesh(new T.SphereGeometry(1,32,18,0,Math.PI*2,0,1.7),hair,head);cap.position.set(0,.545,-.035);cap.scale.set(hw*1.04,.225,.26);
   for(const sign of [-1,1])this.ell(sign*hw*.94,.49,-.04,.042,.12,.19,hair,head);
   if(style==='swept'||style==='short'){
    const quiff=this.ell(-.055,style==='swept'?.735:.69,.055,hw*.98,style==='swept'?.13:.085,.225,hair,head);quiff.rotation.z=-.14;
   }
   if(style==='swept')for(let i=0;i<9;i++)this.tube([[-.25+i*.045,.69,.20],[-.19+i*.045,.80,.06],[-.10+i*.035,.73,-.15]],.012,hair,head);
   if(style==='curly')for(let i=0;i<22;i++){const angle=i*2.4,rad=.23*Math.sqrt(i/22);this.ell(Math.cos(angle)*rad,.70+(.23-rad)*.45,Math.sin(angle)*rad,.075,.070,.077,hair,head)}
   if(style==='bob')for(const sign of [-1,1])this.ell(sign*.28,.35,-.06,.09,.26,.235,hair,head);
   if(style==='ponytail'){this.ell(0,.53,-.29,.13,.14,.14,hair,head);this.ell(0,.25,-.33,.105,.30,.13,hair,head)}
  }
  this.root.scale.setScalar(this.height);this.restPose();
 }
 restPose(){for(const side of ['left','right']){const arm=this.bones[side+'Arm'],leg=this.bones[side+'Leg'];if(arm){arm.upper.quaternion.identity();arm.upper.rotation.z=side==='left'?.12:-.12;arm.lower.quaternion.identity()}if(leg){leg.upper.quaternion.identity();leg.lower.quaternion.identity()}}}
 setLivePose(pose){this.livePose=pose;if(this.fallback)return this.fallback.setLivePose(pose);this.draw()}
 rotate(delta){this.yaw+=delta;if(this.fallback)return this.fallback.rotate(delta);this.draw()}
 draw(){
  if(this.destroyed||!this.model)return;if(this.fallback){this.fallback.yaw=this.yaw;return this.fallback.draw()}
  const T=THREE,live=this.livePose,canvas=this.canvas,w=Math.max(1,canvas.width),h=Math.max(1,canvas.height);
  if(this.renderWidth!==w||this.renderHeight!==h){this.gpu.setSize(w,h,false);this.renderWidth=w;this.renderHeight=h}this.camera.aspect=w/h;this.camera.updateProjectionMatrix();
  this.body.quaternion.identity();this.restPose();this.root.rotation.set(0,live?0:this.yaw,0);this.root.scale.set(this.height*(live?.mirror?-1:1),this.height,this.height);
  if(live){
   const basis=new T.Matrix4().makeBasis(new T.Vector3(...live.x),new T.Vector3(...live.y),new T.Vector3(...live.z));this.body.quaternion.setFromRotationMatrix(basis);
   const inverse=this.body.quaternion.clone().invert(),down=new T.Vector3(0,-1,0);
   for(const [key,group]of [['Arm','arms'],['Leg','legs']])for(const side of ['left','right']){
    const b=this.bones[side+key],p=live[group]?.[side];if(!p)continue;
    const upper=new T.Vector3(...p.upper).applyQuaternion(inverse).normalize(),lower=new T.Vector3(...p.lower).applyQuaternion(inverse).normalize();
    b.upper.quaternion.setFromUnitVectors(down,upper);b.lower.quaternion.setFromUnitVectors(down,lower.applyQuaternion(b.upper.quaternion.clone().invert()));
   }
   // Rotate around hip, then frame every transformed vertex for floor/standing movements.
   this.body.position.set(0,0,0);
   const bounds=new T.Box3().setFromObject(this.root),center=bounds.getCenter(new T.Vector3()),size=bounds.getSize(new T.Vector3());
   const distance=Math.max(size.y,size.x/this.camera.aspect)/(2*Math.tan(31*Math.PI/360))*1.18;
   this.camera.position.set(center.x,center.y,center.z+Math.max(3,distance));this.camera.lookAt(center);this.gpu.setClearColor(0x000000,0);
  }else{
   this.body.position.set(0,Math.sin(this.phase*1.6)*.008,0);
   const distance=Math.max(4.5,2.3/this.camera.aspect)/(2*Math.tan(31*Math.PI/360));this.camera.position.set(0,2.08,distance);this.camera.lookAt(0,1.97,0);this.gpu.setClearColor(0x111c30,0);
  }
  this.gpu.render(this.scene,this.camera);this.onRotate?.(this.yaw);
 }
 cancel(){if(this.frame!==null)cancelAnimationFrame(this.frame);this.frame=null}
 schedule(){if(this.fallback)return this.fallback.schedule();if(this.frame!==null||!this.running||this.destroyed||document.hidden||!this.inView)return;if(this.motion.matches){this.draw();return}this.frame=requestAnimationFrame(t=>{this.frame=null;if(t-this.lastTime>50){this.phase=t/1000;this.lastTime=t;this.draw()}this.schedule()})}
 start(){this.running=true;if(this.fallback)return this.fallback.start();this.schedule()}
 stop(){this.running=false;if(this.fallback)return this.fallback.stop();this.cancel()}
 destroy(){this.stop();this.destroyed=true;if(this.fallback)return this.fallback.destroy();this.events.abort();this.observer?.disconnect();this.resize?.disconnect();this.clear();this.gpu.dispose();this.gpu.forceContextLoss()}
};
