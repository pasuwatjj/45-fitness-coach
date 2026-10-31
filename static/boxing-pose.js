/* Upper-body gesture edges: one punch per extension, recalibrate after tracking loss. */
'use strict';
window.BoxingPose=class {
 constructor(){this.reset()}
 reset(){this.base=null;this.samples=[];this.arms={left:false,right:false};this.last=0;this.dodged=false}
 read(p,w,now){
  const good=i=>p[i]&&p[i].visibility>.6;
  if(![0,11,12,13,14,15,16].every(good)){this.reset();return{valid:false,label:'ให้เห็นหัว ไหล่ ศอก และมือทั้งสองข้าง'}}
  const mid=(a,b,k)=>(p[a][k]+p[b][k])/2,span=Math.hypot(p[11].x-p[12].x,p[11].y-p[12].y);
  if(span<.08)return{valid:false,label:'เข้าใกล้กล้องอีกนิด'};
  const head=(p[0].x-mid(11,12,'x'))/span,depth=(w?.[0]?.z-(w?.[11]?.z+w?.[12]?.z)/2)||0;
  if(!this.base){this.samples.push([head,depth]);if(this.samples.length<20)return{valid:false,label:'ยืนตรง ยกมือการ์ด เพื่อปรับศูนย์…'};this.base=this.samples.reduce((a,v)=>[a[0]+v[0]/20,a[1]+v[1]/20],[0,0]);return{valid:true,action:'idle',label:'พร้อม'}}
  const lean=Math.max(Math.abs(head-this.base[0]),Math.abs(depth-this.base[1])*2.5),dodge=lean>.32;
  if(dodge&&!this.dodged){this.dodged=true;return{valid:true,action:'dodge',label:'โยกหลบ'}}if(lean<.18)this.dodged=false;
  let guard=true;
  for(const [side,s,e,h]of [['left',11,13,15],['right',12,14,16]]){
   const points=w?.length===33?w:p,dist=(a,b)=>Math.hypot(points[a].x-points[b].x,points[a].y-points[b].y,(points[a].z||0)-(points[b].z||0));
   const reach=dist(s,h)/Math.max(.01,dist(s,e)+dist(e,h));
   guard=guard&&p[h].y<p[s].y+.10&&Math.abs(p[h].x-p[0].x)<span*1.4;
   if(reach<.77)this.arms[side]=true;
   if(this.arms[side]&&reach>.92&&now-this.last>400){this.arms[side]=false;this.last=now;return{valid:true,action:side,label:side==='left'?'หมัดซ้าย':'หมัดขวา'}}
  }
  return{valid:true,action:guard?'guard':'idle',label:guard?'ตั้งการ์ด':'พร้อม'};
 }
};
