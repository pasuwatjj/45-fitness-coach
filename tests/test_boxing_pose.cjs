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
// Upper-body-only lateral movement: immediate slip, five-second hold, neutral/reversal reset.
{const {p,read,settle}=fixture();p[23].visibility=p[24].visibility=0;for(const i of [0,11,12,13,14,15,16])p[i].x-=.10;let r=settle(5);assert(r.slip>.5);assert.equal(r.strafe,0);r=settle(60);assert.equal(r.strafe,0);r=settle(12);assert.equal(r.strafe,1);for(const i of [0,11,12,13,14,15,16])p[i].x+=.20;r=settle(8);assert(r.slip<-.5);assert.equal(r.strafe,0);for(const i of [0,11,12,13,14,15,16])p[i].x-=.10;r=settle(10);assert.equal(r.strafe,0);assert.equal(r.sideSeconds,0)}
// Deep bow changes the torso and suppresses forward travel; missing hands do not strike on recovery.
{const {p,settle}=fixture();p[23].visibility=p[24].visibility=0;p[0].z=-.4;let r=settle(15);assert(r.bend>.8);assert.equal(r.move,0);p[0].z=0;r=settle(15);assert(Math.abs(r.bend)<.05);p[15].visibility=0;settle();p[15].visibility=1;assert.equal(settle(3).action,'control')}
console.log('PASS no recoil/hold/jitter bonus punches, deliberate rearm, upper-body 5-second circling, reversal/neutral reset, deep bend and occlusion recovery');
{const {p,d}=fixture();assert.equal(d.read(p,p,10000).valid,false);assert.equal(d.sideAt,null);assert.equal(d.walk,0)}
console.log('PASS stalled tracking recalibrates rather than completing a stale side hold');

// Both depth directions wait five seconds; reversal, neutral and tracking loss cancel progress.
for(const depth of [-.10,.06]){
 const {p,read,settle}=fixture();p[0].z=depth;
 let r=settle(12);assert.equal(r.move,0);assert(r.walkSeconds>0);
 r=settle(45);assert.equal(r.move,0);r=settle(30);assert.equal(r.move,depth<0?1:-1);
 p[0].z=-depth;r=settle(10);assert.equal(r.move,0);assert(r.walkSeconds<1);
 p[0].z=0;r=settle(12);assert.equal(r.move,0);assert.equal(r.walkSeconds,0);
 p[0].z=depth;settle(40);p[0].visibility=0;assert.equal(read().valid,false);
 p[0].visibility=1;p[0].z=0;settle(24);p[0].z=depth;assert.equal(settle(45).move,0);
}
console.log('PASS five-second forward/backward holds; reversal, neutral and tracking-loss reset');
// Lateral holds work in both directions, without a leg landmark requirement.
for(const sign of [-1,1]){
 const {p,settle}=fixture();p[23].visibility=p[24].visibility=0;
 for(const i of [0,11,12,13,14,15,16])p[i].x-=sign*.10;
 assert.equal(settle(50).strafe,0);assert.equal(settle(35).strafe,sign);
 for(const i of [0,11,12,13,14,15,16])p[i].x+=sign*.10;
 assert.equal(settle(15).strafe,0);
}
// Recalibration must clear even a completed hold in the SAME direction.
{const {p,settle}=fixture();p[0].z=.06;assert.equal(settle(90).move,-1);p[0].visibility=0;settle(2);p[0].visibility=1;p[0].z=0;settle(24);p[0].z=.06;assert.equal(settle(50).move,0);assert.equal(settle(35).move,-1)}
console.log('PASS left/right holds and same-direction recalibration reset');
