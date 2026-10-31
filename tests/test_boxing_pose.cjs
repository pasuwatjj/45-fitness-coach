const fs=require('fs'),vm=require('vm'),assert=require('assert');const sandbox={window:{I18N:{lang:'en'}}};vm.runInNewContext(fs.readFileSync('static/boxing-pose.js','utf8'),sandbox);const D=sandbox.window.BoxingPose;
function fixture(){
 const p=Array.from({length:33},()=>({x:.5,y:.5,z:0,visibility:1}));for(const [i,x,y,z]of [[0,.5,.2,0],[11,.35,.4,0],[12,.65,.4,0],[13,.30,.55,-.08],[14,.70,.55,-.08],[15,.4,.3,-.1],[16,.6,.3,-.1],[23,.4,.8,0],[24,.6,.8,0]])Object.assign(p[i],{x,y,z});
 const d=new D();let now=0;const read=()=>d.read(p,p,now+=70),settle=(n=8)=>{let r;for(let i=0;i<n;i++)r=read();return r};settle(24);return{p,d,read,settle};
}
// Front remains responsive, while small backward depth must not be masked by mild forward torso noise.
{const {p,settle}=fixture();p[11].z=p[12].z=-.14;assert.equal(settle().move,1);p[11].z=p[12].z=0;p[0].z=.05;assert.equal(settle().move,-1);p[0].z=0;assert.equal(settle().move,0);p[11].z=p[12].z=-.04;p[0].z=.03;assert.equal(settle().move,-1)}
// Smaller image-space shoulder width provides a fallback when model depth barely changes.
{const {p,settle}=fixture();p[11].x=.365;p[12].x=.635;assert.equal(settle().move,-1);p[11].x=.35;p[12].x=.65;assert.equal(settle().move,0)}
// Partial frame, crouch/stand, loss of head tracking, and English-only feedback.
{const {p,d,settle}=fixture();p[15].visibility=p[16].visibility=.1;p[23].visibility=p[24].visibility=.1;p[0].z=.06;assert.equal(settle().move,-1);p[0].z=0;for(const i of [0,11,12])p[i].y+=.17;let r=settle();assert(r.crouch>.9);assert(!r.guard);assert(!/[ก-๙]/.test(r.label));for(const i of [0,11,12])p[i].y-=.17;assert(settle().crouch<.05);p[0].visibility=.1;assert.equal(settle().valid,false);assert.equal(d.walk,0)}
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
