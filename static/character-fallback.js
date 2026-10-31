/* Original local Canvas 3D renderer. No downloaded model, framework, or CDN. */
'use strict';
window.FitnessBlockFallback=class {
 constructor(canvas){this.canvas=canvas;this.yaw=-.32;this.model=null;this.drag=null;this.onRotate=null;this.phase=0;this.running=false;this.frame=null;this.lastFrame=-Infinity;this.events=new AbortController();this.inView=true;this.intersection=typeof IntersectionObserver==='function'?new IntersectionObserver(entries=>{this.inView=entries[0]?.isIntersecting!==false;this.schedule()}):null;this.intersection?.observe(canvas);this.motion=window.matchMedia?.('(prefers-reduced-motion: reduce)');this.visibility=()=>this.schedule();document.addEventListener('visibilitychange',this.visibility,{signal:this.events.signal});this.motion?.addEventListener('change',this.visibility);canvas.style.touchAction='none';canvas.tabIndex=0;
 canvas.addEventListener('pointerdown',e=>{this.drag={x:e.clientX,yaw:this.yaw};canvas.setPointerCapture?.(e.pointerId)},{signal:this.events.signal});
 canvas.addEventListener('pointermove',e=>{if(!this.drag)return;this.yaw=this.drag.yaw+(e.clientX-this.drag.x)*.012;this.draw()},{signal:this.events.signal});
 const release=()=>this.drag=null;canvas.addEventListener('pointerup',release,{signal:this.events.signal});canvas.addEventListener('pointercancel',release,{signal:this.events.signal});
 canvas.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();this.rotate(e.key==='ArrowLeft'?-.18:.18)}},{signal:this.events.signal});
 }
 start(){if(this.destroyed)return;this.running=true;this.schedule()}
 schedule(){if(this.frame!==null){cancelAnimationFrame(this.frame);this.frame=null}if(!this.running||this.destroyed)return;if(document.hidden||!this.inView||this.motion?.matches||(typeof BrowserCamera!=='undefined'&&BrowserCamera.active)){this.phase=.55;this.draw();return}this.frame=requestAnimationFrame(time=>this.animate(time))}
 animate(time){this.frame=null;if(!this.running||this.destroyed)return;if(!this.canvas.isConnected||this.canvas.closest('[hidden]')){this.stop();return}if(time-this.lastFrame>=1000/30){this.lastFrame=time;this.phase=time/1000;this.draw()}this.schedule()}
 stop(){this.running=false;if(this.frame!==null)cancelAnimationFrame(this.frame);this.frame=null}
 destroy(){this.stop();this.destroyed=true;this.events.abort();this.intersection?.disconnect();this.motion?.removeEventListener('change',this.visibility);this.model=null;this.drag=null}
 rotate(delta){this.yaw+=delta;this.draw()}
 set(model){this.model=model;this.draw()}
 setLivePose(pose){this.livePose=pose;this.draw()}
 draw(){if(!this.model)return;const c=this.canvas,ctx=c.getContext('2d');if(!ctx)return;const W=c.width,H=c.height,live=this.livePose;ctx.clearRect(0,0,W,H);ctx.save();if(live?.mirror){ctx.translate(W,0);ctx.scale(-1,1)}
 if(!live){
 const bg=ctx.createLinearGradient(0,0,W,H);bg.addColorStop(0,'#172943');bg.addColorStop(1,'#091523');ctx.fillStyle=bg;ctx.fillRect(0,0,W,H);
 ctx.strokeStyle='#ffffff08';ctx.lineWidth=1;for(let x=-W;x<W*2;x+=44){ctx.beginPath();ctx.moveTo(x,H*.56);ctx.lineTo(x+W*.5,H);ctx.stroke()}for(let y=H*.65;y<H;y+=28){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke()}
 const glow=ctx.createRadialGradient(W/2,H*.46,0,W/2,H*.46,W*.55);glow.addColorStop(0,'#7e99b92a');glow.addColorStop(1,'#7e99b900');ctx.fillStyle=glow;ctx.fillRect(0,0,W,H);
 ctx.fillStyle='#030c18a8';ctx.beginPath();ctx.ellipse(W/2,H*.89,W*.25,H*.036,0,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#8bd8d84f';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(W/2,H*.89,W*.30,H*.045,0,0,Math.PI*2);ctx.stroke();
 }
 const a=this.model.appearance,g=this.model.growth?.levels||{},arms=this.model.growth?.arm_levels||{};const v=k=>Math.max(0,Math.min(1,g[k]||0)),skin=a.skin_color,hair=a.hair_color,shorts=a.shorts_color,female=a.gender==='female';
 // Adult proportions are stylized; dimensions are recorded, never used to infer muscle.
 const heightScale=this.model.visual?.height_scale||1,waistScale=this.model.visual?.waist_scale||1;
 const scale=live?(live.floor?Math.min(W/4.8,H/3.3):live.full?Math.min(W/4.9,H/4.6):Math.min(W/3.8,H/2.8)):Math.min(W/4.9,H/5.5),cos=Math.cos(live?0:this.yaw),sin=Math.sin(live?0:this.yaw),faces=[];
 const {add,mul,norm,cross}=window.AvatarPose||{};
 const bodyTransform=live?([x,y,z])=>add([0,1.78,0],add(add(mul(live.x,x),mul(live.y,y-1.78)),mul(live.z,z))):p=>p;
 const bone=(origin,target)=>{
  const y=mul(norm(target),-1),x=norm(cross(y,live.z),live.x),z=norm(cross(x,y),live.z),start=bodyTransform(origin);
  return point=>add(start,add(add(mul(x,point[0]-origin[0]),mul(y,point[1]-origin[1])),mul(z,point[2]-origin[2])));
 };
 const project=([x,y,z])=>{const X=x*cos+z*sin,Z=-x*sin+z*cos,Y=y*heightScale;return [W/2+X*scale,live?H/2-(Y-(live.floor?1.78:live.full?2:2.83))*scale+Z*scale*.12:H*.87-Y*scale+Z*scale*.17,Z+Y*.17]};
 const shade=(hex,f)=>{let n=parseInt(hex.slice(1),16);return '#'+[n>>16,(n>>8)&255,n&255].map(v=>Math.round(Math.max(0,Math.min(255,v*f))).toString(16).padStart(2,'0')).join('')};
 const box=(x,y,z,w,h,d,color,decorate=null,transform=null)=>{
 const pts=[[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]].map(([i,j,k])=>{const point=[x+i*w/2,y+j*h/2,z+k*d/2];return project(transform?transform(point):bodyTransform(point))});
 for(const [ids,light] of [[[0,3,2,1],.70],[[4,5,6,7],1.07],[[0,4,7,3],.78],[[1,2,6,5],.9],[[3,7,6,2],1.18],[[0,1,5,4],.6]]){const p=ids.map(i=>pts[i]);const signed=(p[1][0]-p[0][0])*(p[2][1]-p[1][1])-(p[1][1]-p[0][1])*(p[2][0]-p[1][0]);if(signed>=0)continue;faces.push({p,depth:p.reduce((n,a)=>n+a[2],0)/4,color:shade(color,light),decorate:ids[0]===4?decorate:null})}
 };
 const legs=.27+.19*v('legs'),torso=.73+.48*v('back')+.3*v('chest'),depth=.38+.25*v('chest')+.13*v('back'),waist=(female?.57:.64)*waistScale;
 for(const sign of [-1,1]){const x=sign*.25,side=sign<0?'right':'left',pose=live?.legs[side],upper=pose?bone([x,1.65,0],pose.upper):null;
  let lower=null;if(pose){const knee=add(bodyTransform([x,1.65,0]),mul(pose.upper,.7)),local=bone([x,.95,0],pose.lower),base=bodyTransform([x,.95,0]);lower=p=>add(local(p),knee.map((v,i)=>v-base[i]))}
  box(x,.13,.075,.34+legs*.22,.22,.57,'#e9e8e2',null,lower);box(x,.27,.005,.29+legs*.18,.12,.35,'#cbd1d5',null,lower);box(x,.70,0,legs*.85,.8,legs*.93,skin,null,lower);box(x,1.27,0,legs,.62,legs*1.05,skin,null,upper);box(x,1.54,.01,.44+v('legs')*.15,.51,.52+v('legs')*.12,shorts,null,upper)}
 box(0,1.78,0,waist+.14,.15,.50,shorts);box(0,2.02,0,waist,.40,.42,skin);box(0,2.35,0,(waist+torso)/2,.33,depth*.95,skin);box(0,2.73,0,torso,.48,depth,skin);
 if(v('chest')>.08&&!female){for(const sign of [-1,1])box(sign*torso*.235,2.75,depth*.30,torso*.46,.39,depth*.65,skin)}
 if(v('back')>.12){for(const sign of [-1,1])box(sign*torso*.31,2.55,-depth*.31,torso*.35,.64,depth*.60,skin)}
 if(female){box(0,2.74,.012,torso*1.02,.32,depth*1.06,shorts);box(0,2.56,.02,torso*.98,.10,depth*1.08,shorts);for(const sign of [-1,1])box(sign*torso*.30,2.95,.01,.09,.22,depth*1.07,shorts)}
 if(v('chest')+v('back')>.75&&!female){for(const y of [2.06,2.24,2.42])for(const sign of [-1,1])box(sign*.15,y,.23,.26,.14,.07,shade(skin,1.035))}
 const shoulder=.28+.33*v('shoulders');
 // Both forearms pivot at the elbow; hands and dumbbells follow the same joint.
 const curl=.15+(1-Math.cos(this.phase*Math.PI*.8))*.98;
 for(const [sign,side] of [[-1,'right'],[1,'left']]){
  const level=Math.max(0,Math.min(1,arms[side]??v('arms'))),aw=.22+.36*level,x=sign*(torso/2+shoulder*.42),armX=x+sign*.10;
  box(x,2.79,0,shoulder,.38+v('shoulders')*.17,shoulder*1.04,skin);
  const liveArm=live?.arms[side],upper=liveArm?bone([x,2.79,0],liveArm.upper):null;
  box(x+sign*.055,2.39,0,aw,.59,aw*1.12,skin,null,upper);
  let pivot=([px,py,pz])=>{const y=py-2.12;return[px,2.12+y*Math.cos(curl)+pz*Math.sin(curl),-y*Math.sin(curl)+pz*Math.cos(curl)]};
  if(liveArm){const elbow=add(bodyTransform([x,2.79,0]),mul(liveArm.upper,.67)),base=bodyTransform([armX,2.12,0]),lower=bone([armX,2.12,0],liveArm.lower);pivot=p=>add(lower(p),elbow.map((v,i)=>v-base[i]))}
  box(armX,1.87,.02,aw*.78,.51,aw*.85,skin,null,pivot);
  box(armX,1.54,.035,.22+level*.08,.24,.25+level*.07,skin,null,pivot);
  if(!live?.cardio){box(armX,1.49,.05,.64,.09,.09,'#bbc4d5',null,pivot);
  for(const end of [-1,1]){box(armX+end*.29,1.49,.05,.13,.35,.35,'#293c58',null,pivot);box(armX+end*.38,1.49,.05,.07,.25,.25,'#73d1dd',null,pivot)}}
 }
 box(0,3.10,0,.25,.24,.26,skin);box(0,3.53,0,.66,.66,.59,skin,'face');box(0,3.23,.01,.53,.13,.51,skin);
 // Friendly block face on the front surface, visible naturally during rotation.
 if(a.hair!=='bald'){
 box(0,3.88,-.015,.70,.13,.64,hair);box(0,3.60,-.30,.70,.48,.09,hair);
 if(a.hair==='short'){box(-.27,3.72,0,.12,.27,.62,hair);box(.27,3.72,0,.12,.27,.62,hair);box(0,3.81,.30,.67,.12,.09,hair)}
 if(a.hair==='swept'){box(-.15,3.95,0,.42,.18,.64,hair);box(-.22,3.81,.30,.25,.25,.09,hair);box(.16,3.85,.29,.37,.13,.09,hair)}
 if(a.hair==='curly'){for(const x of [-.26,0,.26])for(const z of [-.23,.03,.27])box(x,3.96+(x===0?.05:0),z,.25,.24,.24,hair);box(-.32,3.72,0,.15,.28,.60,hair);box(.32,3.72,0,.15,.28,.60,hair)}
 if(a.hair==='bob'){for(const x of [-.31,.31])box(x,3.56,0,.14,.64,.65,hair);box(0,3.82,.30,.68,.13,.09,hair)}
 if(a.hair==='ponytail'){box(0,3.72,-.42,.24,.40,.28,hair);box(0,3.38,-.47,.22,.46,.25,hair);box(0,3.80,.29,.69,.12,.08,hair);box(0,3.83,-.45,.25,.06,.25,shorts)}
 }
 faces.sort((a,b)=>a.depth-b.depth);for(const f of faces){ctx.beginPath();f.p.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.fillStyle=f.color;ctx.fill();ctx.strokeStyle='#00000012';ctx.lineWidth=.7;ctx.stroke();if(f.decorate==='face'){const quad=(x,y,w,h,color)=>{const points=[[x-w/2,y-h/2,.302],[x+w/2,y-h/2,.302],[x+w/2,y+h/2,.302],[x-w/2,y+h/2,.302]].map(p=>project(bodyTransform(p)));ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.fillStyle=color;ctx.fill()};for(const x of [-.14,.14]){quad(x,3.53,.065,.085,'#242b36');quad(x-.011,3.55,.019,.023,'#fff');quad(x,3.65,.11,.023,hair)}quad(0,3.42,.045,.04,shade(skin,.85));quad(0,3.34,.13,.018,'#8e5245');quad(-.065,3.355,.018,.035,'#8e5245');quad(.065,3.355,.018,.035,'#8e5245')}}
 ctx.restore();if(!live){ctx.fillStyle='#c4d7e7';ctx.font='600 12px sans-serif';ctx.textAlign='center';ctx.fillText('45  /  TRAINING CHARACTER',W/2,H-17);this.onRotate?.(this.yaw);}
 }
};

// Shared, server-backed LV/EXP presentation for own and member profiles/characters.
window.FitnessGrowthPanel=function(growth){
 const en=window.I18N?.lang==='en',t=(th,enText)=>en?enText:th;
 const el=(tag,text='',cls='')=>{const n=document.createElement(tag);n.textContent=text;n.className=cls;return n};
 const box=el('section','','character-growth exp-growth');box.dataset.i18nIgnore='';
 box.append(el('h3',t('LV และ EXP รายส่วน','Body-part LV & EXP')),el('p',t('ครั้งที่ผ่านและบันทึกแล้ว: ผู้เริ่มต้น 10 · Pro 100 · Expert 1,000 EXP/ครั้ง เฉพาะส่วนหลักของท่า','Saved accepted reps: beginner 10 · pro 100 · expert 1,000 EXP/rep, for the exercise’s primary body part.')));
 box.append(el('p',t('เริ่ม LV 1 ที่ 0 EXP · ค่าเลื่อน LV ถัดไป: 10 → 100 → 1,000 → … EXP สะสมส่วนเกินต่อไป ตัวละครโตตาม LV เป็นความก้าวหน้าในเกม','Start LV 1 at 0 EXP. Next-level costs: 10 → 100 → 1,000 → … EXP; excess carries over. Character size follows LV as game progression.')));
 for(const [key,th,name] of [['arms','แขน','Arms'],['chest','อก','Chest'],['back','หลัง','Back'],['legs','ขา','Legs'],['shoulders','ไหล่','Shoulders']]){
  const part=growth?.parts?.[key]||{level:1,exp:0,next_exp:10,total_exp:0,progress:0};
  const row=el('div','','exp-part');row.dataset.part=key;
  const fmt=n=>Number(n).toLocaleString(en?'en-US':'th-TH');
  row.append(el('strong',t(th,name)+' · LV '+part.level),el('span',fmt(part.total_exp)+' EXP '+t('สะสม','total')));
  const bar=el('progress');bar.max=1;bar.value=part.progress;bar.setAttribute('aria-label',t(th,name)+' LV '+part.level+' · '+part.exp+' / '+part.next_exp+' EXP');
  row.append(bar,el('small',fmt(part.exp)+' / '+fmt(part.next_exp)+' EXP '+t('สู่ LV ','to LV ')+(part.level+1)));box.append(row);
 }
 if(growth?.arm_parts)box.append(el('p',t('แขนซ้าย / ขวา: ','Left / right arm: ')+'LV '+growth.arm_parts.left.level+' / LV '+growth.arm_parts.right.level));
 box.append(el('small',t('เซตเก่าที่ผ่านการตรวจสอบแต่ไม่มีระดับ ใช้อัตราผู้เริ่มต้น · เซตที่ไม่มีผลตรวจสอบไม่เพิ่ม EXP · ไม่นับรอบผิดหรือรอบที่ยังยืนยันไม่ได้ · ไม่ใช่มวลกล้ามเนื้อจริง','Verified older sets without saved difficulty use beginner. Sets without verification, rejected attempts and unverified attempts earn no EXP. This does not measure real muscle mass.')));
 return box;
};
