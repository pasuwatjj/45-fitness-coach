const fs=require('fs'),vm=require('vm'),assert=require('assert');const sandbox={window:{I18N:{lang:'en'}}};vm.runInNewContext(fs.readFileSync('static/boxing-pose.js','utf8'),sandbox);const D=sandbox.window.BoxingPose;
function fixture(){
 const p=Array.from({length:33},()=>({x:.5,y:.5,z:0,visibility:1}));for(const [i,x,y,z]of [[0,.5,.2,0],[11,.35,.4,0],[12,.65,.4,0],[13,.30,.55,-.08],[14,.70,.55,-.08],[15,.4,.3,-.1],[16,.6,.3,-.1],[23,.4,.8,0],[24,.6,.8,0]])Object.assign(p[i],{x,y,z});
 const d=new D();let now=0;const read=()=>d.read(p,p,now+=70),settle=(n=8)=>{let r;for(let i=0;i<n;i++)r=read();return r};settle(24);return{p,d,read,settle};
}
// Front remains responsive, while small backward depth must not be masked by mild forward torso noise.
{const {p,settle}=fixture();p[11].z=p[12].z=-.14;assert.equal(settle(82).move,1);p[11].z=p[12].z=0;p[0].z=.05;assert.equal(settle(82).move,-1);p[0].z=0;assert.equal(settle().move,0);p[11].z=p[12].z=-.04;p[0].z=.03;assert.equal(settle(82).move,-1)}
// Smaller image-space shoulder width provides a fallback when model depth barely changes.
{const {p,settle}=fixture();p[11].x=.365;p[12].x=.635;assert.equal(settle(82).move,-1);p[11].x=.35;p[12].x=.65;assert.equal(settle().move,0)}
// Partial frame, crouch/stand, loss of head tracking, and English-only feedback.
{const {p,d,settle}=fixture();p[15].visibility=p[16].visibility=.1;p[23].visibility=p[24].visibility=.1;p[0].z=.06;assert.equal(settle(82).move,-1);p[0].z=0;for(const i of [0,11,12])p[i].y+=.17;let r=settle();assert(r.crouch>.9);assert(!r.guard);assert(!/[ก-๙]/.test(r.label));for(const i of [0,11,12])p[i].y-=.17;assert(settle().crouch<.05);p[0].visibility=.1;assert.equal(settle().valid,false);assert.equal(d.walk,0)}
for(const side of ['left','right'])for(const type of ['straight','hook','uppercut']){
 const {p,read,settle}=fixture(),s=side==='left'?11:12,e=s+2,h=s+4,sign=side==='left'?1:-1;
 if(type==='straight'){Object.assign(p[e],{x:p[s].x+sign*.035,y:.43,z:-.15});Object.assign(p[h],{x:p[s].x+sign*.08,y:.36,z:-.3})}
 if(type==='hook'){Object.assign(p[e],{x:p[s].x-sign*.13,y:.4,z:-.1});Object.assign(p[h],{x:p[s].x+sign*.20,y:.36,z:-.12})}
 if(type==='uppercut'){
  Object.assign(p[h],{x:p[s].x,y:.62,z:-.07});settle();Object.assign(p[e],{x:p[s].x,y:.54,z:-.13});Object.assign(p[h],{x:p[s].x,y:.31,z:-.18});
 }
 const r=read();assert.equal(r.action,side,`${side} ${type}: ${r.label}`);assert.equal(r.punchType,type,`${side} expected ${type}, got ${r.punchType}`);for(let i=0;i<15;i++)assert.equal(read().action,'control','held arm must not repeatedly strike');
}
// Guard activation remains a 3-second elbow hold.
{const {p,settle}=fixture();p[13].y=p[14].y=.4;const r=settle(50);assert(r.guard);assert.equal(r.guardSeconds,3)}
console.log('PASS mild backward lean, depth conflict, perspective fallback, crouch/stand, cropped/occluded body, assisted left/right straight/hook/uppercut, hold suppression, guard and English');
// Retraction, held extension and small jitter never create a bonus uppercut/hook.
for(const side of ['left','right']){
 const {p,read,settle}=fixture(),s=side==='left'?11:12,e=s+2,h=s+4,sign=side==='left'?1:-1,neutral=JSON.parse(JSON.stringify(p));
 const extend=()=>{Object.assign(p[e],{x:p[s].x+sign*.035,y:.43,z:-.15});Object.assign(p[h],{x:p[s].x+sign*.08,y:.36,z:-.3})};extend();assert.equal(read().action,side);settle(12);
 for(const i of [e,h])Object.assign(p[i],neutral[i]);assert.equal(read().action,'control');for(let i=0;i<8;i++)assert.equal(read().action,'control');
 extend();assert.equal(read().action,side);for(let i=0;i<20;i++){p[h].x+=(i%2?1:-1)*.005;assert.equal(read().action,'control')}
}
// Upper-body-only lateral movement: immediate slip, two-second hold, neutral/reversal reset.
{const {p,read,settle}=fixture();p[23].visibility=p[24].visibility=0;for(const i of [0,11,12,13,14,15,16])p[i].x-=.10;let r=settle(5);assert(r.slip>.5);assert.equal(r.strafe,0);r=settle(18);assert.equal(r.strafe,0);r=settle(12);assert.equal(r.strafe,1);for(const i of [0,11,12,13,14,15,16])p[i].x+=.20;r=settle(8);assert(r.slip<-.5);assert.equal(r.strafe,0);for(const i of [0,11,12,13,14,15,16])p[i].x-=.10;r=settle(10);assert.equal(r.strafe,0);assert.equal(r.sideSeconds,0)}
// Deep bow changes the torso and suppresses forward travel; missing hands do not strike on recovery.
{const {p,settle}=fixture();p[23].visibility=p[24].visibility=0;p[0].z=-.4;let r=settle(15);assert(r.bend>.8);assert.equal(r.move,0);p[0].z=0;r=settle(15);assert(Math.abs(r.bend)<.05);p[15].visibility=0;settle();p[15].visibility=1;assert.equal(settle(3).action,'control')}
console.log('PASS no recoil/hold/jitter bonus punches, deliberate rearm, upper-body 2-second circling, reversal/neutral reset, deep bend and occlusion recovery');
{const {p,d}=fixture();assert.equal(d.read(p,p,10000).valid,false);assert.equal(d.sideAt,null);assert.equal(d.walk,0)}
console.log('PASS stalled tracking recalibrates rather than completing a stale side hold');

// Both depth directions wait two seconds; reversal, neutral and tracking loss cancel progress.
for(const depth of [-.10,.06]){
 const {p,read,settle}=fixture();p[0].z=depth;
 let r=settle(12);assert.equal(r.move,0);assert(r.walkSeconds>0);
 r=settle(10);assert.equal(r.move,0);r=settle(14);assert.equal(r.move,depth<0?1:-1);
 p[0].z=-depth;r=settle(10);assert.equal(r.move,0);assert(r.walkSeconds<1);
 p[0].z=0;r=settle(12);assert.equal(r.move,0);assert.equal(r.walkSeconds,0);
 p[0].z=depth;settle(40);p[0].visibility=0;assert.equal(read().valid,false);
 p[0].visibility=1;p[0].z=0;settle(24);p[0].z=depth;assert.equal(settle(22).move,0);
}
console.log('PASS two-second forward/backward holds; reversal, neutral and tracking-loss reset');
// Lateral holds work in both directions, without a leg landmark requirement.
for(const sign of [-1,1]){
 const {p,settle}=fixture();p[23].visibility=p[24].visibility=0;
 for(const i of [0,11,12,13,14,15,16])p[i].x-=sign*.10;
 assert.equal(settle(24).strafe,0);assert.equal(settle(12).strafe,sign);
 for(const i of [0,11,12,13,14,15,16])p[i].x+=sign*.10;
 assert.equal(settle(15).strafe,0);
}
// Recalibration must clear even a completed hold in the SAME direction.
{const {p,settle}=fixture();p[0].z=.06;assert.equal(settle(90).move,-1);p[0].visibility=0;settle(2);p[0].visibility=1;p[0].z=0;settle(24);p[0].z=.06;assert.equal(settle(24).move,0);assert.equal(settle(12).move,-1)}
console.log('PASS left/right holds and same-direction recalibration reset');

// Short forearm-only jabs score once, retract without scoring, and rearm for the next jab.
for(const side of ['left','right']){
 const {p,d,read,settle}=fixture(),s=side==='left'?11:12,e=s+2,h=s+4,sign=side==='left'?1:-1;
 Object.assign(p[e],{x:p[s].x-sign*.01,y:.46,z:-.10});Object.assign(p[h],{x:p[s].x,y:.38,z:-.17});d.reset();settle(24);
 for(let trial=0;trial<2;trial++){
  Object.assign(p[h],{y:.40,z:-.22});const r=read();assert.equal(r.action,side,'short jab');assert.equal(r.punchType,'straight');
  for(let i=0;i<10;i++)assert.equal(read().action,'control','held jab');
  Object.assign(p[h],{y:.38,z:-.17});for(let i=0;i<10;i++)assert.equal(read().action,'control','jab recoil');
 }
}
// Arm directions and elbow extension must retain full measured lateral/depth range.
{const {p,settle}=fixture();Object.assign(p[13],{x:.20,y:.40,z:-.15});Object.assign(p[15],{x:.05,y:.40,z:-.30});const a=settle(20).arms.left;assert(Math.abs(a.upper[0])>.69);assert(Math.abs(a.upper[2])>.69);assert(a.upper.reduce((sum,v,i)=>sum+v*a.lower[i],0)>.999)}
// Gentle leans animate immediately but neither jitter nor short leans move the fighter.
for(const depth of [-.045,.03]){const {p,settle}=fixture();p[0].z=depth;let r=settle(20);assert(Math.abs(r.bend)>.13);assert.equal(r.move,0);r=settle(15);assert.equal(r.move,depth<0?1:-1)}
{const {p,read}=fixture();for(let i=0;i<100;i++){p[0].x=.5+(i%2?1:-1)*.002;p[0].z=(i%2?1:-1)*.002;const r=read();assert.equal(r.move,0);assert.equal(r.strafe,0);assert.equal(r.action,'control')}}
console.log('PASS short jabs/rearm, faithful full arm vectors, gentle leans, and neutral jitter');
// Boundary: at 1,999 ms the lean is still only a dodge; at 2,000 ms movement starts.
for(const direction of ['left','right','forward','back']){
 const {p,d,settle}=fixture();
 if(direction==='left'||direction==='right')p[0].x+=direction==='left'?-.06:.06;else p[0].z=direction==='forward'?-.05:.035;
 settle(5);const lateral=direction==='left'||direction==='right',start=lateral?d.sideAt:d.walkAt;
 assert(start!==null);for(let at=d.lastTime+100;at<start+1999;at+=100)d.read(p,p,at);
 const before=d.read(p,p,start+1999),after=d.read(p,p,start+2000);
 assert.equal(lateral?before.strafe:before.move,0);assert.notEqual(lateral?after.strafe:after.move,0);
}
console.log('PASS exact 1,999/2,000 ms boundary in all four directions');
