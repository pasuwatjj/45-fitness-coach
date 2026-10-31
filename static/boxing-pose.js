'use strict';
window.BoxingPose=class {
 constructor(){this.reset()}
 reset(){this.base=null;this.samples=[];this.arms={left:{armed:false,last:0},right:{armed:false,last:0}};this.smooth={};this.walk=0;this.guardAt=null;this.lastTime=null}
 read(p,w,now){
  const good=i=>p[i]&&p[i].visibility>.5&&['x','y','z'].every(k=>Number.isFinite(p[i][k]));
  if(![0,11,12,13,14,15,16].every(good)){this.reset();return{valid:false,action:'idle',guard:false,move:0,label:'ให้เห็นหัว ไหล่ ศอก และมือทั้งสองข้าง'}}
  const world=w?.length===33&&[0,11,12,13,14,15,16].every(i=>w[i]&&['x','y','z'].every(k=>Number.isFinite(w[i][k]))),q=world?w:p;
  const span=Math.max(.1,Math.hypot(q[11].x-q[12].x,q[11].y-q[12].y,q[11].z-q[12].z));
  const torso=good(23)&&good(24)?Math.atan2((q[11].z+q[12].z-q[23].z-q[24].z)/2,Math.max(.12,(q[23].y+q[24].y-q[11].y-q[12].y)/2)):null;
  const head=Math.atan2(q[0].z-(q[11].z+q[12].z)/2,Math.max(.1,(q[11].y+q[12].y)/2-q[0].y));
  const arms={};let punch=null;const dt=this.lastTime===null?33:Math.min(100,now-this.lastTime);this.lastTime=now;const alpha=1-Math.exp(-dt/55);
  for(const [side,s,e,h]of [['left',11,13,15],['right',12,14,16]]){
   const v=(a,b)=>[q[b].x-q[a].x,-(q[b].y-q[a].y),-(q[b].z-q[a].z)],norm=v=>{const l=Math.hypot(...v)||1;return v.map(x=>x/l)},u=norm(v(s,e)),l=norm(v(e,h));
   // Camera-facing movement maps forward into the fixed-facing fighter, never rotates its root.
   const mapped=a=>[a[0]*.35,a[1],Math.max(-.25,a[2])];
   const target={upper:norm(mapped(u)),lower:norm(mapped(l))};
   if(!this.smooth[side])this.smooth[side]=target;
   for(const part of ['upper','lower'])this.smooth[side][part]=norm(target[part].map((v,i)=>this.smooth[side][part][i]+alpha*(v-this.smooth[side][part][i])));
   arms[side]=this.smooth[side];const a=this.arms[side],dot=u.reduce((sum,x,i)=>sum+x*l[i],0),depth=(q[s].z-q[h].z)/span;
   if(dot<.55||depth<.18)a.armed=true;
   const facing=q[h].y<q[s].y+.28&&depth>.38;
   if(a.armed&&dot>.70&&facing&&now-a.last>450){a.armed=false;a.last=now;punch=side}
  }
  if(!this.base){this.samples.push([torso,head]);if(this.samples.length>=20)this.base={torso:torso===null?null:this.samples.reduce((a,v)=>a+(v[0]||0),0)/20,head:this.samples.reduce((a,v)=>a+v[1],0)/20};return{valid:false,arms,move:0,guard:false,action:'idle',label:'ยืนตรง มองกล้อง เพื่อปรับศูนย์…'}}
  const angle=-((torso!==null&&this.base.torso!==null)?torso-this.base.torso:head-this.base.head)*180/Math.PI;
  if(Math.abs(angle)>27)this.walk=angle>0?1:-1;else if(Math.abs(angle)<17)this.walk=0;
  const raised=[['left',11,13],['right',12,14]].every(([side,s,e])=>Math.abs(q[e].y-q[s].y)/span<.32);
  if(raised&&!punch)this.guardAt??=now;else this.guardAt=null;
  const held=this.guardAt===null?0:Math.min(3,(now-this.guardAt)/1000);
  return{valid:true,arms,move:this.walk,guard:raised&&!punch,guardSeconds:held,angle,action:punch||'control',label:punch?(punch==='left'?'หมัดซ้าย':'หมัดขวา'):raised?`ยกศอกการ์ด ${held.toFixed(1)}/3 วิ`:this.walk>0?'เดินหน้า':this.walk<0?'ถอยหลัง':'พร้อม · แขนตามท่าจริง'};
 }
};
