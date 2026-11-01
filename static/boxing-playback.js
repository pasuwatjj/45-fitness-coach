'use strict';
// Short position interpolation buffer; it never changes combat or authoritative state.
window.BoxingPlayback=class{
 constructor(){this.reset()}
 reset(){this.frames=new Map();this.stamp=-Infinity}
 push(players,stamp,now){if(stamp<=this.stamp)return;this.stamp=stamp;for(const p of players){if(!Number.isFinite(p.x)||!Number.isFinite(p.z))continue;const frames=this.frames.get(p.uid)||[];frames.push({x:p.x,z:p.z,stamp,at:now,moving:!!(p.move||p.side),hit:p.hit_at||0});this.frames.set(p.uid,frames.slice(-6))}}
 sample(uid,now,own=false,input=null){const f=this.frames.get(uid);if(!f?.length)return null;const t=now-(own?0:80),last=f[f.length-1];
  // Brief local movement preview follows current input, never stale server controls.
  // Combat remains authoritative; limit the preview to 19 cm and respect separation.
  if(own&&input?.enabled){const q=input.opponent,age=Math.max(0,now-last.at)/1000;
   if(!q||input.kick||now-(input.hitAt??-Infinity)<180)return{x:last.x,z:last.z};
   const dx=q.x-last.x,dz=q.z-last.z,d=Math.hypot(dx,dz)||1,move=input.move||0,side=input.strafe||0,n=Math.max(1,Math.hypot(move,side)),ahead=Math.min(.18,age),scale=1.05*ahead/n;
   let v=this.clamp(last.x+(dx/d*move+dz/d*side)*scale,last.z+(dz/d*move-dx/d*side)*scale);
   const gap=Math.hypot(v.x-q.x,v.z-q.z);if(gap<.8){const k=Math.min(1,Math.max(0,(d-.8)/Math.max(.001,d-gap)));v={x:last.x+(v.x-last.x)*k,z:last.z+(v.z-last.z)*k}}return v;
  }
 for(let i=1;i<f.length;i++){const a=f[i-1],b=f[i];if(t>=a.at&&t<=b.at){const v=(t-a.at)/Math.max(1,b.at-a.at);return{x:a.x+(b.x-a.x)*v,z:a.z+(b.z-a.z)*v}}}
  if(t<f[0].at)return{x:f[0].x,z:f[0].z};const prev=f[f.length-2];if(!prev||!last.moving||last.hit!==prev.hit)return{x:last.x,z:last.z};const dt=Math.max(.016,(last.stamp-prev.stamp)/1000),dx=(last.x-prev.x)/dt,dz=(last.z-prev.z)/dt,scale=Math.min(1,3.15/Math.max(.001,Math.hypot(dx,dz))),ahead=Math.min(.25,Math.max(0,t-last.at)/1000);return this.clamp(last.x+dx*scale*ahead,last.z+dz*scale*ahead);
 }
 clamp(x,z){for(let n=0;n<2;n++)for(let i=0;i<8;i++){const nx=Math.cos(i*Math.PI/4),nz=Math.sin(i*Math.PI/4),over=x*nx+z*nz-5;if(over>0){x-=nx*over;z-=nz*over}}return{x,z}}
};
