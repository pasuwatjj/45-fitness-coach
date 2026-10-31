'use strict';
window.BoxingPose=class {
 constructor(){this.reset()}
 reset(){this.base=null;this.samples=[];this.arms={left:{armed:true,last:-1000,history:[]},right:{armed:true,last:-1000,history:[]}};this.smooth={};this.walk=0;this.walkAt=null;this.walkDirection=0;this.guardAt=null;this.lastTime=null;this.lean=0;this.crouch=0;this.space=null;this.sideAt=null;this.side=0;this.slip=0;this.bend=0;this.gesture=0}
 read(p=[],w,now){
  if(this.lastTime!==null&&now-this.lastTime>700)this.reset();
  const good=i=>p[i]&&p[i].visibility>.5&&['x','y','z'].every(k=>Number.isFinite(p[i][k]));
  const t=(th,en)=>window.I18N?.lang==='en'?en:th;
  const invalid=label=>({valid:false,action:'idle',guard:false,move:0,crouch:0,slip:0,bend:0,strafe:0,sideSeconds:0,label});
  if(![0,11,12].every(good)){this.reset();return invalid(t('ให้เห็นหัวและไหล่ทั้งสองข้าง','Keep your head and both shoulders visible'))}
  const finite=(a,i)=>a[i]&&['x','y','z'].every(k=>Number.isFinite(a[i][k]));
  const world=w?.length===33&&[0,11,12].every(i=>finite(w,i)),q=world?w:p;
  if(this.space!==null&&this.space!==world)this.reset();this.space=world;
  const span=Math.max(.1,Math.hypot(q[11].x-q[12].x,q[11].y-q[12].y,q[11].z-q[12].z));
  const imageSpan=Math.max(.06,Math.hypot(p[11].x-p[12].x,p[11].y-p[12].y)),shoulderY=(p[11].y+p[12].y)/2;
  const torso=[23,24].every(i=>good(i)&&finite(q,i))?Math.atan2((q[11].z+q[12].z-q[23].z-q[24].z)/2,Math.max(.12,(q[23].y+q[24].y-q[11].y-q[12].y)/2)):null;
  const head=Math.atan2(q[0].z-(q[11].z+q[12].z)/2,Math.max(.1,(q[11].y+q[12].y)/2-q[0].y));
  const dt=this.lastTime===null?33:Math.max(1,Math.min(150,now-this.lastTime));this.lastTime=now;
  const alpha=1-Math.exp(-dt/65),arms={},candidates=[];
  for(const [side,s,e,h]of [['left',11,13,15],['right',12,14,16]]){
   const a=this.arms[side];
   if(![s,e,h].every(i=>good(i)&&finite(q,i))){a.armed=false;a.home=null;a.end=null;a.history=[];a.recoverAt=null;delete this.smooth[side];arms[side]={upper:[0,-1,0],lower:[0,-1,0]};continue}
   const v=(a,b)=>[q[b].x-q[a].x,-(q[b].y-q[a].y),-(q[b].z-q[a].z)],norm=v=>{const l=Math.hypot(...v)||1;return v.map(x=>x/l)},u=norm(v(s,e)),l=norm(v(e,h));
   const mapped=a=>norm(a),target={upper:mapped(u),lower:mapped(l)};
   if(!this.smooth[side])this.smooth[side]=target;
   for(const part of ['upper','lower']){const previous=this.smooth[side][part],change=Math.hypot(...target[part].map((v,i)=>v-previous[i])),blend=change>.25?1-Math.exp(-dt/30):alpha;this.smooth[side][part]=norm(target[part].map((v,i)=>previous[i]+blend*(v-previous[i])))}
   arms[side]=this.smooth[side];const hand=v(s,h).map(x=>x/span),dot=u.reduce((sum,x,i)=>sum+x*l[i],0),distance=Math.hypot(...hand);
   if(!a.armed){
    const nearLaunch=a.launch&&Math.hypot(...hand.map((v,i)=>v-a.launch[i]))<a.launchTolerance;
    const neutral=nearLaunch||(dot<.65&&hand[2]<.6&&distance<1.15)||hand[1]<-.9;
    const returned=!a.end||Math.hypot(...hand.map((v,i)=>v-a.end[i]))>(a.retractDistance??.38);
    if(neutral&&returned)a.recoverAt??=now;else a.recoverAt=null;
    a.history=[];a.home=hand;
    if(a.recoverAt!==null&&now-a.recoverAt>=180){a.armed=true;a.recoverAt=null}
    continue; // Retraction is never an attack, including the frame which rearms.
   }
   a.home??=hand;a.history.push({v:hand,time:now,dot});a.history=a.history.filter(x=>now-x.time<=350);
   const old=a.history[0],delta=hand.map((v,i)=>v-old.v[i]),travel=hand.map((v,i)=>v-a.home[i]),elapsed=Math.max(.07,(now-old.time)/1000);
   const speed=Math.hypot(...delta)/elapsed,forward=Math.max(delta[2],travel[2]),up=Math.max(delta[1],travel[1]),across=Math.max(Math.abs(delta[0]),Math.abs(travel[0]));
   const nearHead=hand[1]>-.55, moving=speed>1.0;
   let type=null,score=0;
   if(moving&&nearHead&&up>.32&&dot<.82&&hand[2]>-.3){type='uppercut';score=up}
   else if(moving&&nearHead&&across>.36&&dot<.92&&hand[2]>-.25){type='hook';score=across}
   else if(nearHead&&forward>.24&&hand[2]>.25&&dot>.35&&moving){type='straight';score=forward}
   // A short jab can extend the forearm without a full upper-arm swing.
   else if(nearHead&&forward>.10&&hand[2]>.12&&speed>.5&&dot-old.dot>.12&&distance-Math.hypot(...old.v)>.06){type='straight';score=forward}
   if(this.base&&a.armed&&type&&now-a.last>400)candidates.push({side,type,score,hand});
   // While relaxed, keep a recent neutral hand position rather than a stale launch point.
   if(a.armed&&!type&&speed<.25){a.home=hand}
  }
  if(!this.base){
   const hipX=good(23)&&good(24)?(p[23].x+p[24].x)/2:(p[11].x+p[12].x)/2;
   this.samples.push({torso,head,imageSpan,shoulderY,headY:p[0].y,centerX:p[0].x*.65+(p[11].x+p[12].x)*.175,lateral:(p[0].x-hipX)/imageSpan});
   if(this.samples.length>=20){const median=key=>{const values=this.samples.map(v=>v[key]).filter(v=>v!==null).sort((a,b)=>a-b);return values.length?values[Math.floor(values.length/2)]:null};this.base=Object.fromEntries(['torso','head','imageSpan','shoulderY','headY','centerX','lateral'].map(k=>[k,median(k)]))}
   return{...invalid(t('ยืนตรง มองกล้อง เพื่อปรับศูนย์…','Stand upright and face the camera to calibrate…')),arms};
  }
  const chosen=candidates.sort((a,b)=>b.score-a.score)[0];let punch=null,punchType='straight';
  if(chosen){punch=chosen.side;punchType=chosen.type;const a=this.arms[punch];a.armed=false;a.last=now;a.launch=a.home?.slice();a.launchTolerance=Math.max(.04,Math.min(.15,Math.hypot(...chosen.hand.map((v,i)=>v-(a.home?.[i]??v)))*.35));a.retractDistance=Math.max(.07,Math.min(.38,Math.hypot(...chosen.hand.map((v,i)=>v-(a.home?.[i]??v)))*.55));a.end=chosen.hand;a.recoverAt=null;a.history=[];this.gesture++}
  const torsoAngle=torso!==null&&this.base.torso!==null?-(torso-this.base.torso)*180/Math.PI:0,headAngle=-(head-this.base.head)*180/Math.PI;
  // Backward lean is usually smaller. Do not let a small forward torso estimate mask it.
  const back=Math.min(torsoAngle,headAngle),front=Math.max(torsoAngle,headAngle*.85);
  let angle=back<-6&&front<10?back:Math.abs(torsoAngle)>7?torsoAngle:headAngle*.85;
  const facing=Math.abs(q[11].z-q[12].z)/span<.5;
  const scaleChange=imageSpan/this.base.imageSpan-1;
  if(facing&&Math.abs(angle)<7){if(scaleChange<-.045)angle=-10;else if(scaleChange>.065)angle=13}
  this.lean+=(angle-this.lean)*(1-Math.exp(-dt/95));
  if(this.lean>10)this.walk=1;else if(this.lean<-6)this.walk=-1;else if(Math.abs(this.lean)<3)this.walk=0;
  const drop=Math.min(shoulderY-this.base.shoulderY,p[0].y-this.base.headY)/this.base.imageSpan;
  const squat=Math.max(0,Math.min(1,(drop-.08)/.36));this.crouch+=(squat-this.crouch)*alpha;
  // Anatomical left follows the shoulder labels, independent of mirrored preview.
  const hipX=good(23)&&good(24)?(p[23].x+p[24].x)/2:(p[11].x+p[12].x)/2;
  const leftSign=Math.sign(p[11].x-p[12].x)||1;
  const lateral=(good(23)&&good(24)?(p[0].x-hipX)/this.base.imageSpan-this.base.lateral:(p[0].x*.65+(p[11].x+p[12].x)*.175-this.base.centerX)/this.base.imageSpan)*leftSign;
  const targetSlip=Math.max(-1,Math.min(1,lateral/.32));this.slip+=(targetSlip-this.slip)*alpha;
  this.bend+=(Math.max(-.65,Math.min(1,this.lean/45))-this.bend)*alpha;
  const side=Math.abs(this.slip)>.35?Math.sign(this.slip):0;
  if(!side){this.side=0;this.sideAt=null}else if(side!==this.side){this.side=side;this.sideAt=now}
  const sideSeconds=this.sideAt===null?0:Math.min(2,(now-this.sideAt)/1000),strafe=sideSeconds>=2?this.side:0;
  // Deep waist bends are ducks, not a request to charge forward into the opponent.
  if(this.bend>.60||this.crouch>.50)this.walk=0;
  // A continuous deliberate lean is required in every direction, not just laterally.
  if(!this.walk){this.walkAt=null;this.walkDirection=0}
  else if(this.walkDirection!==this.walk){this.walkDirection=this.walk;this.walkAt=now}
  const walkSeconds=this.walkAt===null?0:Math.min(2,(now-this.walkAt)/1000),move=walkSeconds>=2?this.walk:0;
  const raised=[['left',11,13,15],['right',12,14,16]].every(([side,s,e,h])=>good(e)&&good(h)&&finite(q,e)&&Math.abs(q[e].y-q[s].y)/span<.32);
  if(raised&&!punch)this.guardAt??=now;else this.guardAt=null;
  const held=this.guardAt===null?0:Math.min(3,(now-this.guardAt)/1000),names={straight:t('หมัดตรง','Straight'),hook:t('ฮุก','Hook'),uppercut:t('อัปเปอร์คัต','Uppercut')};
  return{valid:true,arms,move,walkSeconds,crouch:this.crouch,slip:this.slip,bend:this.bend,strafe,sideSeconds,gesture:this.gesture,guard:raised&&!punch,guardSeconds:held,angle:this.lean,action:punch||'control',punchType,label:punch?`${punch==='left'?t('ซ้าย','Left'):t('ขวา','Right')} · ${names[punchType]}`:side?`${side>0?t('โยกซ้าย','Lean left'):t('โยกขวา','Lean right')} · ${sideSeconds.toFixed(1)}/2 ${t('วิ','s')}${strafe?t(' · เดินวน',' · circling'):''}`:this.walk?`${this.walk>0?t('เอนหน้า','Lean forward'):t('เอนหลัง','Lean backward')} · ${walkSeconds.toFixed(1)}/2 ${t('วิ','s')}${move?t(' · กำลังเดิน',' · walking'):''}`:raised?`${t('ยกศอกการ์ด','Guard hold')} ${held.toFixed(1)}/3 ${t('วิ','s')}`:this.crouch>.3?t('ย่อตัว','Crouching'):this.walk>0?t('เดินหน้า','Forward'):this.walk<0?t('ถอยหลัง','Backward'):t('พร้อม · แขนตามท่าจริง','Ready · arms follow your movement')};
 }
};
