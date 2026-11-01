'use strict';
window.BoxingPose=class {
 constructor(){this.reset()}
 reset(){this.base=null;this.samples=[];this.arms={left:{armed:true,last:-1000,history:[]},right:{armed:true,last:-1000,history:[]}};this.smooth={};this.walk=0;this.walkAt=null;this.walkDirection=0;this.guardAt=null;this.lastTime=null;this.lean=0;this.crouch=0;this.space=null;this.sideAt=null;this.side=0;this.slip=0;this.bend=0;this.gesture=0;this.facingSign=null;this.travelAt=null;this.travelDirection=null;this.travelReady=false;this.neutralAt=null;this.posture={turn:0,hipTurn:0,tilt:0,headPitch:0,headYaw:0,headRoll:0};this.faceAt=null;this.lowerBody={confidence:0,shiftX:0,shiftZ:0,drop:0,hipRoll:0,leftKnee:0,rightKnee:0,stance:0,stagger:0}}
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
  // Use the fighter's horizontal shoulder frame, not the camera axes. Keep vertical
  // tilt intact so waist bends are animated independently of turning to punch.
  const vector=(a,b)=>[q[b].x-q[a].x,-(q[b].y-q[a].y),-(q[b].z-q[a].z)],dot=(a,b)=>a.reduce((n,v,i)=>n+v*b[i],0);
  const shoulder=vector(12,11),width=Math.hypot(shoulder[0],shoulder[2]);
  if(width<span*.25){this.reset();return invalid(t('ให้กล้องเห็นแนวไหล่ชัดเจน','Keep the shoulder line visible'))}
  this.facingSign??=Math.sign(shoulder[0])||1;
  const left=[shoulder[0]/width,0,shoulder[2]/width],front=[-left[2]*this.facingSign,0,left[0]*this.facingSign];
  const local=v=>[dot(v,left),v[1],dot(v,front)];
  const hips=[23,24].every(i=>good(i)&&finite(q,i));
  const torsoVector=hips?vector(23,11).map((v,i)=>(v+vector(24,12)[i])/2):null;
  const headVector=vector(11,0).map((v,i)=>(v+vector(12,0)[i])/2);
  const torso=hips?Math.atan2(-dot(torsoVector,front),Math.max(.12,torsoVector[1])):null;
  const bodyLateral=hips?local(vector(23,0).map((v,i)=>(v+vector(24,0)[i])/2))[0]/span:null;
  const head=Math.atan2(-dot(headVector,front),Math.max(.1,headVector[1]));
  const heading=Math.atan2(front[0],front[2]),roll=Math.atan2(shoulder[1],width);
  const hipLine=hips?vector(24,23):null,hipHeading=hipLine?Math.atan2(-hipLine[2]*this.facingSign,hipLine[0]*this.facingSign):null;
  const faceGood=[7,8].every(i=>good(i)&&finite(q,i))&&Math.hypot(...vector(8,7))>span*.18;
  const faceVector=faceGood?local(vector(7,0).map((v,i)=>(v+vector(8,0)[i])/2)):null;
  const faceValid=faceVector&&faceVector[2]>span*.06&&Math.hypot(...faceVector)<span*.95;
  const facePitch=faceValid?Math.atan2(-faceVector[1],faceVector[2]):null,faceYaw=faceValid?Math.atan2(faceVector[0],faceVector[2]):null;
  const faceLine=faceValid?vector(8,7):null,faceRoll=faceLine?Math.atan2(faceLine[1],Math.hypot(faceLine[0],faceLine[2])):null;
  const neckVector=faceValid?vector(11,7).map((v,i)=>(v+vector(12,8)[i])/2):null,neckPitch=neckVector?Math.atan2(-dot(neckVector,front),Math.max(.1,neckVector[1])):null;
  const legVisible=[23,24,25,26,27,28].every(i=>good(i)&&finite(q,i)&&p[i].x>-.05&&p[i].x<1.05&&p[i].y>-.05&&p[i].y<1.05);
  const legLengths=legVisible?[...['left','right'].map((_,i)=>[Math.hypot(...vector(23+i,25+i))/span,Math.hypot(...vector(25+i,27+i))/span])]:[];
  const legs=legVisible&&legLengths.every(a=>a.every(l=>l>.35&&l<3))&&(q[27].y+q[28].y-q[23].y-q[24].y)/2>span*1.1;
  const support=legs?local(vector(27,23).map((v,i)=>(v+vector(28,24)[i])/2)).map(v=>v/span):null;
  const feet=legs?local(vector(28,27)).map(v=>v/span):null,hipRoll=hips?Math.atan2(hipLine[1],Math.hypot(hipLine[0],hipLine[2])):null;
  const dt=this.lastTime===null?33:Math.max(1,Math.min(150,now-this.lastTime));this.lastTime=now;
  const alpha=1-Math.exp(-dt/65),arms={},candidates=[];
  for(const [side,s,e,h]of [['left',11,13,15],['right',12,14,16]]){
   const a=this.arms[side];
   const raw=[s,e,h].every(i=>finite(q,i))?[vector(s,e),vector(e,h)]:null;
   // When both segments point into the lens, recover depth from stable limb lengths.
   // This is gated by visible joints, forward depth and foreshortening of BOTH links.
   const foreshortened=raw&&a.reference&&[s,e,h].every(good)&&raw.every((v,i)=>Math.hypot(v[0],v[1])<a.reference[i]*span*.55&&v[2]>span*.025)&&local(raw[0].map((v,i)=>v+raw[1][i]))[2]>span*.12;
   if(foreshortened)for(let i=0;i<2;i++){const v=raw[i],length=a.reference[i]*span;v[2]=Math.max(v[2],Math.sqrt(Math.max(0,length*length-v[0]*v[0]-v[1]*v[1])))}
   if(![s,e,h].every(i=>good(i)&&finite(q,i))||[[s,e],[e,h]].some(([a,b])=>{const length=Math.hypot(...(foreshortened?raw[a===s?0:1]:vector(a,b)))/span;return length<.12||length>1.8})){a.armed=false;a.home=null;a.end=null;a.history=[];a.recoverAt=null;arms[side]=this.smooth[side]&&now-(a.visibleAt??-1000)<200?this.smooth[side]:{upper:[side==='left'?.25:-.25,-.5,.65],lower:[side==='left'?-.15:.15,.8,.4]};continue}
   if(!foreshortened&&raw.every(v=>Math.hypot(v[0],v[1])>Math.hypot(...v)*.65)){
    a.lengths??=[];a.lengths.push(raw.map(v=>Math.hypot(...v)/span));if(a.lengths.length>25)a.lengths.shift();
    a.reference=[0,1].map(i=>a.lengths.map(v=>v[i]).sort((x,y)=>x-y)[Math.floor(a.lengths.length/2)]);
   }
   const v=(a,b)=>local(foreshortened?(a===s&&b===e?raw[0]:a===e&&b===h?raw[1]:raw[0].map((x,i)=>x+raw[1][i])):vector(a,b)),norm=v=>{const l=Math.hypot(...v)||1;return v.map(x=>x/l)},u=norm(v(s,e)),l=norm(v(e,h));
   a.visibleAt=now;const mapped=a=>norm(a),target={upper:mapped(u),lower:mapped(l)};
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
   this.samples.push({supportX:support?.[0]??null,supportZ:support?.[2]??null,supportY:support?.[1]??null,stance:feet?Math.abs(feet[0]):null,stagger:feet?.[2]??null,hipRoll,neckPitch,heading,hipHeading,roll,facePitch,faceYaw,faceRoll,torso,head,bodyLateral,torsoHeight:torsoVector?.[1]??null,headHeight:headVector[1],imageSpan,shoulderY,headY:p[0].y,centerX:p[0].x*.65+(p[11].x+p[12].x)*.175,lateral:(p[0].x-hipX)/imageSpan});
   if(this.samples.length>=20){const median=key=>{const values=this.samples.map(v=>v[key]).filter(v=>v!==null).sort((a,b)=>a-b);return values.length?values[Math.floor(values.length/2)]:null};this.base=Object.fromEntries(['supportX','supportZ','supportY','stance','stagger','hipRoll','neckPitch','heading','hipHeading','roll','facePitch','faceYaw','faceRoll','torso','head','bodyLateral','torsoHeight','headHeight','imageSpan','shoulderY','headY','centerX','lateral'].map(k=>[k,median(k)]))}
   return{...invalid(t('ยืนตรง มองกล้อง เพื่อปรับศูนย์…','Stand upright and face the camera to calibrate…')),arms};
  }
  const clamp=(v,limit=1)=>Math.max(-limit,Math.min(limit,v)),angleDelta=(a,b)=>Math.atan2(Math.sin(a-b),Math.cos(a-b));
  const turn=clamp(angleDelta(heading,this.base.heading)/1.05),hipTurn=hipHeading!==null&&this.base.hipHeading!==null?clamp(angleDelta(hipHeading,this.base.hipHeading)/1.05):turn*.25;
  const targets={turn,hipTurn,tilt:clamp(angleDelta(roll,this.base.roll)/.6)};
  if(faceValid){
   this.faceAt=now;for(const key of ['facePitch','faceYaw','faceRoll'])if(this.base[key]===null)this.base[key]=({facePitch,faceYaw,faceRoll})[key];
   targets.headPitch=clamp((angleDelta(facePitch,this.base.facePitch)+(hips&&this.base.torso!==null?torso-this.base.torso:0))/.65);targets.headYaw=clamp(angleDelta(faceYaw,this.base.faceYaw)/.75);targets.headRoll=clamp(angleDelta(faceRoll,this.base.faceRoll)/.55);
  }else if(this.faceAt===null||now-this.faceAt>200)Object.assign(targets,{headPitch:0,headYaw:0,headRoll:0});
  for(const [key,value]of Object.entries(targets))this.posture[key]+=(value-this.posture[key])*(1-Math.exp(-dt/(key.startsWith('head')?100:75)));
  const lowerTargets={confidence:0,shiftX:0,shiftZ:0,drop:0,hipRoll:0,leftKnee:0,rightKnee:0,stance:0,stagger:0};
  if(legs){
   // Allow a cropped calibration to acquire a lower-body reference once feet become visible.
   for(const [key,value]of Object.entries({supportX:support[0],supportZ:support[2],supportY:support[1],stance:Math.abs(feet[0]),stagger:feet[2],hipRoll}))this.base[key]??=value;
   const knee=i=>{const u=vector(23+i,25+i),l=vector(25+i,27+i);return Math.acos(clamp(dot(u,l)/(Math.hypot(...u)*Math.hypot(...l))))/1.8};
   Object.assign(lowerTargets,{confidence:1,shiftX:clamp((support[0]-this.base.supportX)/.6),shiftZ:clamp((support[2]-this.base.supportZ)/.6),drop:Math.max(0,clamp((1-support[1]/this.base.supportY)/.45)),hipRoll:clamp((hipRoll-this.base.hipRoll)/.45),leftKnee:clamp(knee(0)),rightKnee:clamp(knee(1)),stance:clamp((Math.abs(feet[0])-this.base.stance)/.8),stagger:clamp((feet[2]-this.base.stagger)/.8)});
  }
  for(const [key,value]of Object.entries(lowerTargets))this.lowerBody[key]+=(value-this.lowerBody[key])*(1-Math.exp(-dt/110));
  const chosen=candidates.sort((a,b)=>b.score-a.score)[0];let punch=null,punchType='straight';
  if(chosen){punch=chosen.side;punchType=chosen.type;const a=this.arms[punch];a.armed=false;a.last=now;a.launch=a.home?.slice();a.launchTolerance=Math.max(.04,Math.min(.15,Math.hypot(...chosen.hand.map((v,i)=>v-(a.home?.[i]??v)))*.35));a.retractDistance=Math.max(.07,Math.min(.38,Math.hypot(...chosen.hand.map((v,i)=>v-(a.home?.[i]??v)))*.55));a.end=chosen.hand;a.recoverAt=null;a.history=[];this.gesture++}
  const torsoAngle=torso!==null&&this.base.torso!==null?-(torso-this.base.torso)*180/Math.PI:0,headAngle=-(neckPitch!==null&&this.base.neckPitch!==null?neckPitch-this.base.neckPitch:head-this.base.head)*180/Math.PI;
  // Backward lean is usually smaller. Do not let a small forward torso estimate mask it.
  const back=Math.min(torsoAngle,headAngle),forwardAngle=Math.max(torsoAngle,headAngle*.85);
  let angle=back<-6&&forwardAngle<10?back:Math.abs(torsoAngle)>7?torsoAngle:headAngle*.85;
  // Shoulder width changes with yaw and perspective, not just backward leaning.
  // Do not translate that ambiguous signal into a back bend or retreat.
  const fold=hips&&this.base.torsoHeight>0?1-torsoVector[1]/this.base.torsoHeight:0,headFold=this.base.headHeight>0?1-headVector[1]/this.base.headHeight:0;
  if(fold>.16&&headFold>.12)angle=Math.max(angle,Math.min(45,(fold-.08)*100));
  // Reliable torso and face landmarks separate a head look-up from a whole-body lean.
  if(faceValid&&hips&&this.base.torso!==null)angle=fold>.16&&headFold>.12?Math.max(torsoAngle,Math.min(45,(fold-.08)*100)):torsoAngle;
  angle=Math.max(hips?-38:-28,Math.min(65,angle));
  this.lean+=(angle-this.lean)*(1-Math.exp(-dt/95));
  const nod=((p[0].y-shoulderY)-(this.base.headY-this.base.shoulderY))/this.base.imageSpan,forwardIntent=this.lean>7||nod>.12;
  if(forwardIntent)this.walk=1;else if(this.lean<-6)this.walk=-1;else if(Math.abs(this.lean)<3&&nod<.06)this.walk=0;
  const drop=Math.min(shoulderY-this.base.shoulderY,p[0].y-this.base.headY)/this.base.imageSpan;
  const squat=Math.max(0,Math.min(1,(drop-.08)/.36));this.crouch+=(squat-this.crouch)*alpha;
  // Anatomical left follows the shoulder labels, independent of mirrored preview.
  const hipX=good(23)&&good(24)?(p[23].x+p[24].x)/2:(p[11].x+p[12].x)/2;
  const leftSign=Math.sign(p[11].x-p[12].x)||1;
  const lateral=hips&&this.base.bodyLateral!==null?bodyLateral-this.base.bodyLateral:((p[0].x*.65+(p[11].x+p[12].x)*.175-this.base.centerX)/this.base.imageSpan)*leftSign;
  const targetSlip=Math.max(-1,Math.min(1,lateral/.32));this.slip+=(targetSlip-this.slip)*alpha;
  this.bend+=(Math.max(-.85,Math.min(1,this.lean/45))-this.bend)*alpha;
  const side=Math.abs(this.slip)>.35?Math.sign(this.slip):0;
  if(this.crouch>.50&&!forwardIntent)this.walk=0;
  const direction=side+':'+this.walk,hasDirection=!!(side||this.walk);
  if(!hasDirection){
   this.neutralAt??=now;
   // Crossing the centre briefly while switching directions does not restart a walk.
   if(!this.travelReady||now-this.neutralAt>=250){this.travelReady=false;this.travelAt=null;this.travelDirection=null}
  }else{
   if(this.neutralAt!==null&&now-this.neutralAt>=250){this.travelReady=false;this.travelAt=null}
   this.neutralAt=null;
   if(!this.travelReady&&(this.travelAt===null||direction!==this.travelDirection))this.travelAt=now;
   this.travelDirection=direction;
   if(this.travelAt!==null&&now-this.travelAt>=2000)this.travelReady=true;
  }
  this.side=side;this.sideAt=side?this.travelAt:null;this.walkAt=this.walk?this.travelAt:null;this.walkDirection=this.walk;
  const seconds=this.travelReady?2:this.travelAt===null?0:Math.min(2,(now-this.travelAt)/1000);
  const sideSeconds=side?seconds:0,walkSeconds=this.walk?seconds:0,strafe=this.travelReady?side:0,move=this.travelReady?this.walk:0;
  const raised=[['left',11,13,15],['right',12,14,16]].every(([side,s,e,h])=>good(e)&&good(h)&&finite(q,e)&&Math.abs(q[e].y-q[s].y)/span<.32);
  if(raised&&!punch)this.guardAt??=now;else this.guardAt=null;
  const held=this.guardAt===null?0:Math.min(3,(now-this.guardAt)/1000),names={straight:t('หมัดตรง','Straight'),hook:t('ฮุก','Hook'),uppercut:t('อัปเปอร์คัต','Uppercut')};
  return{valid:true,lowerBody:{...this.lowerBody},posture:{...this.posture},arms,move,walkSeconds,crouch:this.crouch,slip:this.slip,bend:this.bend,strafe,sideSeconds,gesture:this.gesture,guard:raised&&!punch,guardSeconds:held,angle:this.lean,action:punch||'control',punchType,label:punch?`${punch==='left'?t('ซ้าย','Left'):t('ขวา','Right')} · ${names[punchType]}`:move&&strafe?`${t('เดินเฉียง','Walk diagonally')} ${move>0?t('หน้า','forward'):t('หลัง','back')} ${strafe>0?t('ซ้าย','left'):t('ขวา','right')}`:side?`${side>0?t('โยกซ้าย','Lean left'):t('โยกขวา','Lean right')} · ${sideSeconds.toFixed(1)}/2 ${t('วิ','s')}${strafe?t(' · เดินวน',' · circling'):''}`:this.walk?`${this.walk>0?t('เอนหน้า','Lean forward'):t('เอนหลัง','Lean backward')} · ${walkSeconds.toFixed(1)}/2 ${t('วิ','s')}${move?t(' · กำลังเดิน',' · walking'):''}`:raised?`${t('ยกศอกการ์ด','Guard hold')} ${held.toFixed(1)}/3 ${t('วิ','s')}`:this.crouch>.3?t('ย่อตัว','Crouching'):this.walk>0?t('เดินหน้า','Forward'):this.walk<0?t('ถอยหลัง','Backward'):t('พร้อม · แขนตามท่าจริง','Ready · arms follow your movement')};
 }
};
