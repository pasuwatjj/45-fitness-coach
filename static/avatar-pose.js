'use strict';
// Visual retargeting only. Never used for repetition, form or reward decisions.
window.AvatarPose=(()=>{
 const add=(a,b)=>a.map((v,i)=>v+b[i]),sub=(a,b)=>a.map((v,i)=>v-b[i]),mul=(a,n)=>a.map(v=>v*n),dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0),cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
 const norm=(a,f=[0,-1,0])=>{const n=Math.hypot(...a);return n>.0001?mul(a,1/n):f.slice()};
 function context(s){const cardio=s?.cardio,exercise=cardio?.mode==='pushup'?'pushup':s?.exercise||'curl';const floor=['pushup','bench_press','floor_press','fly','chest_fly','pullover','lying_triceps'].includes(exercise);const full=!!cardio&&cardio.mode!=='upper'||s?.focus==='full';const bend=floor||['row','bent_over_row','single_row','bent_row','supported_row','incline_press','reverse_fly','rdl','goblet_squat','split_squat'].includes(exercise);return{exercise,cardio:!!cardio,floor,full,bend};}
 function neutral(s){const c=context(s),x=c.floor?[0,0,1]:[1,0,0],y=c.floor?[-1,0,0]:[0,1,0],z=cross(x,y),down=mul(y,-1);return {...c,valid:false,mirror:false,x,y,z,arms:{left:{upper:c.floor?[0,-1,0]:down,lower:c.floor?[0,-1,0]:down},right:{upper:c.floor?[0,-1,0]:down,lower:c.floor?[0,-1,0]:down}},legs:{left:{upper:down,lower:down},right:{upper:down,lower:down}}};}
 function solve(sample,s,now=Date.now()){
  const rest=neutral(s),p=sample?.points;
  if(!s?.running||s.paused||s.person_count>1||!p||p.length!==33||sample.set_id!==s.set_id||now-sample.at>600||now<sample.at||(!s.cardio&&s.tracking?.status?.[0]!=='locked'))return rest;
  const seen=i=>p[i]&&Number.isFinite(p[i][0]+p[i][1])&&p[i][2]>=.5&&p[i][0]>-.15&&p[i][0]<1.15&&p[i][1]>-.15&&p[i][1]<1.15;
  if(!seen(11)||!seen(12))return rest;
  const world=sample.world,hasWorld=world?.length===33&&world.every(v=>v?.length>=3&&v.every(Number.isFinite))&&Math.hypot(...sub(world[11],world[12]))>.025;
  const at=i=>hasWorld?[world[i][0],-world[i][1],-world[i][2]]:[p[i][0]*(sample.aspect||4/3),-p[i][1],0];
  const shoulders=mul(add(at(11),at(12)),.5),hips=seen(23)&&seen(24)?mul(add(at(23),at(24)),.5):null;
  let x=norm(sub(at(11),at(12)),[1,0,0]),up=hips?norm(sub(shoulders,hips),[0,1,0]):[0,1,0];
  if(!rest.bend&&dot(up,[0,1,0])<.55)return rest;
  let y=norm(sub(up,mul(x,dot(up,x))),[0,1,0]),z=norm(cross(x,y),[0,0,1]);y=norm(cross(z,x),y);
  // If floor pose is not visible yet, use a horizontal ready pose, not a curl.
  if(rest.floor&&!hips)return rest;
  const down=mul(y,-1),vector=(a,b,f)=>seen(a)&&seen(b)?norm(sub(at(b),at(a)),f):f.slice();
  const arms={};for(const [side,a,b,c]of[['left',11,13,15],['right',12,14,16]])arms[side]={upper:vector(a,b,down),lower:vector(b,c,down)};
  const legs={};for(const [side,a,b,c]of[['left',23,25,27],['right',24,26,28]])legs[side]=rest.full?{upper:vector(a,b,down),lower:vector(b,c,down)}:{upper:down,lower:down};
  return{...rest,valid:true,mirror:!!sample.mirrored,x,y,z,arms,legs,hasWorld};
 }
 function createStabilizer(){
  let previous=null,lastValid=0,lastAt=0,key=null;
  const reset=()=>{previous=null;lastValid=0;lastAt=0;key=null};
  const blend=(a,b,k)=>a.map((v,i)=>v+(b[i]-v)*k);
  function update(target,state,now=Date.now()){
   const id=state.set_id+':'+state.exercise+':'+state.cardio?.mode;
   if(key!==id){reset();key=id}
   const unsafe=!state.running||state.paused||state.person_count>1||['ambiguous','lost'].includes(state.tracking?.status?.[0]);
   if(unsafe){previous=null;lastValid=0;lastAt=now;return target}
   if(!target.valid){
    if(previous&&now-lastValid<=350)return {...previous,valid:false,held:true};
    previous=null;lastAt=now;return target;
   }
   const k=1-Math.exp(-Math.min(100,Math.max(1,now-lastAt))/45);
   let out=target;
   if(previous&&previous.floor===target.floor&&previous.mirror===target.mirror){
    out={...target};
    for(const a of ['x','y','z'])out[a]=norm(blend(previous[a],target[a],k),target[a]);
    // Re-orthogonalize body orientation after smoothing.
    out.z=norm(cross(out.x,out.y),target.z);out.y=norm(cross(out.z,out.x),target.y);
    for(const group of ['arms','legs']){out[group]={};for(const side of ['left','right']){out[group][side]={};for(const bone of ['upper','lower'])out[group][side][bone]=norm(blend(previous[group][side][bone],target[group][side][bone],k),target[group][side][bone]);}}
   }
   previous=out;lastAt=now;lastValid=now;return out;
  }
  return{update,reset};
 }
 return{solve,neutral,context,createStabilizer,add,sub,mul,dot,cross,norm};
})();
