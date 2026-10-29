'use strict';
// Visual filtering only. Raw observations still go to the server's quality gate.
window.PoseStability=class{
 constructor(){this.reset()}
 reset(){this.old=null;this.at=0;this.pending=new Map();this.display=null}
 apply(body,now,aspect=1){
  if(!body?.length){this.reset();return body}
  const good=p=>p&&p[2]>=.6&&Number.isFinite(p[0]+p[1]),dist=(a,b)=>Math.hypot((a[0]-b[0])*aspect,a[1]-b[1]);
  const out=body.map(p=>p.slice()),saved=body.map(p=>p.slice()),dt=now-this.at;
  if(this.old&&dt>=0&&dt<650){
   for(const[i0,neighbors]of Object.entries({11:[12,13,23],12:[11,14,24],13:[11,15],14:[12,16],23:[11,24,25],24:[12,23,26]})){
    const i=Number(i0);if(!good(body[i])||!good(this.old[i]))continue;
    const ns=neighbors.filter(j=>good(body[j])&&good(this.old[j]));if(ns.length<2)continue;
    const dx=ns.reduce((s,j)=>s+(body[j][0]-this.old[j][0])*aspect,0)/ns.length,dy=ns.reduce((s,j)=>s+body[j][1]-this.old[j][1],0)/ns.length;
    const residual=Math.hypot((body[i][0]-this.old[i][0])*aspect-dx,body[i][1]-this.old[i][1]-dy);
    const distorted=ns.filter(j=>{const a=dist(this.old[i],this.old[j]),b=dist(body[i],body[j]);return a>.06&&(b/a>1.9||b/a<.45)}).length;
    if(residual>.13&&distorted>=2){let pending=this.pending.get(i);pending=!pending||dist(pending.p,body[i])>.07?{p:body[i],at:now,n:1}:{p:body[i],at:pending.at,n:pending.n+1};this.pending.set(i,pending);if(pending.n<3||now-pending.at<120){out[i][2]=0;saved[i]=this.old[i].slice();continue}}
    this.pending.delete(i);
   }
  }else{this.pending.clear();this.display=null}
  this.old=saved;this.at=now;
  if(this.display&&dt>0&&dt<250){for(let i=0;i<out.length;i++){if(!good(out[i])||!good(this.display[i]))continue;const movement=dist(out[i],this.display[i]);const tau=movement>.06?18:45,k=1-Math.exp(-dt/tau);out[i][0]=this.display[i][0]+k*(out[i][0]-this.display[i][0]);out[i][1]=this.display[i][1]+k*(out[i][1]-this.display[i][1])}}
  this.display=out.map(p=>p.slice());return out;
 }
};
