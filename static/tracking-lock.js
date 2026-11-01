'use strict';
// Short-term geometric target lock. Never fills missing joints or freezes a pose.
window.PoseTargetLock=class{
 constructor(){this.reset()}
 reset(){this.locked=false;this.anchor=null;this.velocity={x:0,y:0};this.seen=-Infinity;this.status='waiting'}
 feature(p){if(!p||p.length!==33)return null;const ids=[11,12,23,24].filter(i=>p[i]&&(p[i].visibility??0)>=.45&&Number.isFinite(p[i].x+p[i].y)&&p[i].x>=-.15&&p[i].x<=1.15&&p[i].y>=-.15&&p[i].y<=1.15);if(ids.length<2)return null;const x=ids.reduce((n,i)=>n+p[i].x,0)/ids.length,y=ids.reduce((n,i)=>n+p[i].y,0)/ids.length,scale=Math.max(...ids.flatMap(i=>ids.map(j=>Math.hypot(p[i].x-p[j].x,p[i].y-p[j].y))));if(scale<.035)return null;return{x,y,scale,points:ids.map(i=>[i,p[i].x,p[i].y])}}
 pin(now=performance.now()){if(!this.anchor||this.status!=='tracking'||now-this.seen>750)return false;this.locked=true;this.velocity={x:0,y:0};return true}
 unlock(){this.reset()}
 update(payload,now=performance.now()){
  const rows=payload.poses||[payload.pose||[]],features=rows.map((p,i)=>({i,f:this.feature(p)})).filter(v=>v.f);
  const empty=()=>{this.status='recovering';return{...payload,pose:[],world:[],poses:[],worlds:[]}};
  let chosen;
  if(!this.locked){if(features.length!==1){this.anchor=null;this.status='waiting';return payload}chosen=features[0]}
  else{if(!features.length)return empty();const a=this.anchor,dt=Math.min(.35,Math.max(0,(now-this.seen)/1000)),old=new Map(a.points.map(p=>[p[0],[p[1]+this.velocity.x*dt,p[2]+this.velocity.y*dt]]));
   const ranked=features.map(v=>{const common=v.f.points.filter(p=>old.has(p[0]));return{...v,d:common.length?common.reduce((n,p)=>n+Math.hypot(p[1]-old.get(p[0])[0],p[2]-old.get(p[0])[1]),0)/common.length/Math.max(.1,a.scale):Infinity}}).sort((a,b)=>a.d-b.d);
   chosen=ranked[0];if(chosen.d>1.2||ranked[1]&&ranked[1].d-chosen.d<.35||ranked.some(v=>v!==chosen&&Math.hypot(v.f.x-chosen.f.x,v.f.y-chosen.f.y)<Math.max(.16,Math.min(v.f.scale,chosen.f.scale)*.85)))return empty();
  }
  if(this.anchor&&now>this.seen&&now-this.seen<600){const dt=(now-this.seen)/1000;for(const k of ['x','y'])this.velocity[k]=.5*this.velocity[k]+.5*Math.max(-2,Math.min(2,(chosen.f[k]-this.anchor[k])/dt))}else this.velocity={x:0,y:0};
  this.anchor=chosen.f;this.seen=now;this.status='tracking';if(!this.locked)return payload;
  const pose=rows[chosen.i],world=(payload.worlds||[payload.world||[]])[chosen.i]||[];return{...payload,pose,world,poses:[pose],worlds:[world]};
 }
};
