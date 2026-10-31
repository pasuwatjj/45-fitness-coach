'use strict';
window.BoxingPose=class {
 constructor(){this.reset()}
 reset(){this.base=null;this.samples=[];this.arms={left:{armed:true,last:-1000,history:[]},right:{armed:true,last:-1000,history:[]}};this.smooth={};this.walk=0;this.guardAt=null;this.lastTime=null;this.lean=0;this.crouch=0;this.space=null}
 read(p=[],w,now){
  const good=i=>p[i]&&p[i].visibility>.5&&['x','y','z'].every(k=>Number.isFinite(p[i][k]));
  const t=(th,en)=>window.I18N?.lang==='en'?en:th;
  const invalid=label=>({valid:false,action:'idle',guard:false,move:0,crouch:0,label});
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
   if(![s,e,h].every(i=>good(i)&&finite(q,i))){a.armed=false;a.home=null;a.end=null;a.history=[];delete this.smooth[side];arms[side]={upper:[0,-1,0],lower:[0,-1,0]};continue}
   const v=(a,b)=>[q[b].x-q[a].x,-(q[b].y-q[a].y),-(q[b].z-q[a].z)],norm=v=>{const l=Math.hypot(...v)||1;return v.map(x=>x/l)},u=norm(v(s,e)),l=norm(v(e,h));
   const mapped=a=>norm([a[0]*.35,a[1],Math.max(-.25,a[2])]),target={upper:mapped(u),lower:mapped(l)};
   if(!this.smooth[side])this.smooth[side]=target;
   for(const part of ['upper','lower'])this.smooth[side][part]=norm(target[part].map((v,i)=>this.smooth[side][part][i]+alpha*(v-this.smooth[side][part][i])));
   arms[side]=this.smooth[side];const hand=v(s,h).map(x=>x/span),dot=u.reduce((sum,x,i)=>sum+x*l[i],0),distance=Math.hypot(...hand);
   if(!a.armed&&(!a.end||hand[1]<-.55||hand[2]<a.end[2]-.18||distance<Math.hypot(...a.end)-.22)){a.armed=true;a.home=hand;a.history=[]}
   a.home??=hand;a.history.push({v:hand,time:now});a.history=a.history.filter(x=>now-x.time<=350);
   const old=a.history[0],delta=hand.map((v,i)=>v-old.v[i]),travel=hand.map((v,i)=>v-a.home[i]),elapsed=Math.max(.07,(now-old.time)/1000);
   const speed=Math.hypot(...delta)/elapsed,forward=Math.max(delta[2],travel[2]),up=Math.max(delta[1],travel[1]),across=Math.max(Math.abs(delta[0]),Math.abs(travel[0]));
   const nearHead=hand[1]>-.55, moving=speed>.65;
   let type=null,score=0;
   if(moving&&nearHead&&up>.24&&dot<.82&&hand[2]>-.3){type='uppercut';score=up}
   else if(moving&&nearHead&&across>.28&&dot<.92&&hand[2]>-.25){type='hook';score=across}
   else if(nearHead&&forward>.18&&hand[2]>.22&&dot>.35&&(moving||forward>.35)){type='straight';score=forward}
   if(this.base&&a.armed&&type&&now-a.last>400)candidates.push({side,type,score,hand});
   // While relaxed, keep a recent neutral hand position rather than a stale launch point.
   if(a.armed&&!type&&speed<.25){a.home=hand}
  }
  if(!this.base){
   this.samples.push({torso,head,imageSpan,shoulderY,headY:p[0].y});
   if(this.samples.length>=20){const median=key=>{const values=this.samples.map(v=>v[key]).filter(v=>v!==null).sort((a,b)=>a-b);return values.length?values[Math.floor(values.length/2)]:null};this.base=Object.fromEntries(['torso','head','imageSpan','shoulderY','headY'].map(k=>[k,median(k)]))}
   return{...invalid(t('ยืนตรง มองกล้อง เพื่อปรับศูนย์…','Stand upright and face the camera to calibrate…')),arms};
  }
  const chosen=candidates.sort((a,b)=>b.score-a.score)[0];let punch=null,punchType='straight';
  if(chosen){punch=chosen.side;punchType=chosen.type;const a=this.arms[punch];a.armed=false;a.last=now;a.end=chosen.hand;a.history=[]}
  const torsoAngle=torso!==null&&this.base.torso!==null?-(torso-this.base.torso)*180/Math.PI:0,headAngle=-(head-this.base.head)*180/Math.PI;
  // Backward lean is usually smaller. Do not let a small forward torso estimate mask it.
  const back=Math.min(torsoAngle,headAngle),front=Math.max(torsoAngle,headAngle*.85);
  let angle=back<-8&&front<14?back:Math.abs(torsoAngle)>10?torsoAngle:headAngle*.85;
  const facing=Math.abs(q[11].z-q[12].z)/span<.5;
  const scaleChange=imageSpan/this.base.imageSpan-1;
  if(facing&&Math.abs(angle)<10){if(scaleChange<-.055)angle=-14;else if(scaleChange>.085)angle=18}
  this.lean+=(angle-this.lean)*(1-Math.exp(-dt/95));
  if(this.lean>14)this.walk=1;else if(this.lean<-8)this.walk=-1;else if(Math.abs(this.lean)<5)this.walk=0;
  const drop=Math.min(shoulderY-this.base.shoulderY,p[0].y-this.base.headY)/this.base.imageSpan;
  const squat=Math.max(0,Math.min(1,(drop-.12)/.42));this.crouch+=(squat-this.crouch)*alpha;
  const raised=[['left',11,13,15],['right',12,14,16]].every(([side,s,e,h])=>good(e)&&good(h)&&finite(q,e)&&Math.abs(q[e].y-q[s].y)/span<.32);
  if(raised&&!punch)this.guardAt??=now;else this.guardAt=null;
  const held=this.guardAt===null?0:Math.min(3,(now-this.guardAt)/1000),names={straight:t('หมัดตรง','Straight'),hook:t('ฮุก','Hook'),uppercut:t('อัปเปอร์คัต','Uppercut')};
  return{valid:true,arms,move:this.walk,crouch:this.crouch,guard:raised&&!punch,guardSeconds:held,angle:this.lean,action:punch||'control',punchType,label:punch?`${punch==='left'?t('ซ้าย','Left'):t('ขวา','Right')} · ${names[punchType]}`:raised?`${t('ยกศอกการ์ด','Guard hold')} ${held.toFixed(1)}/3 ${t('วิ','s')}`:this.crouch>.3?t('ย่อตัว','Crouching'):this.walk>0?t('เดินหน้า','Forward'):this.walk<0?t('ถอยหลัง','Backward'):t('พร้อม · แขนตามท่าจริง','Ready · arms follow your movement')};
 }
};
