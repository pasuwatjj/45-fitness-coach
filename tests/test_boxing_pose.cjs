const fs=require('fs'),vm=require('vm'),assert=require('assert');const sandbox={window:{}};vm.runInNewContext(fs.readFileSync('static/boxing-pose.js','utf8'),sandbox);const D=sandbox.window.BoxingPose;
function points(){const p=Array.from({length:33},()=>({x:0,y:0,z:0,visibility:1}));for(const [i,x,y,z]of [[0,0,-.3,0],[11,-.2,0,0],[12,.2,0,0],[13,-.25,.15,-.08],[14,.25,.15,-.08],[15,-.15,-.1,-.1],[16,.15,-.1,-.1],[23,-.15,.5,0],[24,.15,.5,0]])Object.assign(p[i],{x,y,z});return p}
let now=0;const p=points(),d=new D(),read=()=>d.read(p,p,now+=70),settle=()=>{let r;for(let i=0;i<6;i++)r=read();return r};for(let i=0;i<22;i++)read();
let r=read();assert(!r.guard);assert.equal(r.move,0);const old=r.arms.left.lower[1];p[15].y=.5;p[15].z=0;r=read();assert(r.arms.left.lower[1]<old);assert(!['left','right'].includes(r.action));
p[13].y=.02;p[14].y=.02;r=read();assert(r.guard);assert.equal(r.guardSeconds,0);for(let i=0;i<45;i++)r=read();assert.equal(r.guardSeconds,3);p[13].y=.15;assert(!read().guard);
p[15].y=-.1;p[15].z=-.1;read();Object.assign(p[13],{x:-.2,y:0,z:-.25});Object.assign(p[15],{x:-.2,y:0,z:-.5});assert.equal(read().action,'left');assert.notEqual(settle().action,'left');
// ~22-degree torso tilt starts walking; neutral stops without oscillating.
p[11].z=p[12].z=-.2;assert.equal(settle().move,1);p[11].z=p[12].z=.2;assert.equal(settle().move,-1);p[11].z=p[12].z=0;assert.equal(settle().move,0);
// Hands outside frame must disable strikes/guard, not calibrated body movement.
p[15].visibility=p[16].visibility=.1;p[11].z=p[12].z=-.2;r=settle();assert(r.valid);assert.equal(r.move,1);assert(!r.guard);assert.equal(r.action,'control');
// Upper-body framing without hips uses head/shoulder depth in both directions.
const crop=points();crop[23].visibility=crop[24].visibility=.1;const c=new D();const readCrop=()=>c.read(crop,crop,now+=70);for(let i=0;i<22;i++)readCrop();crop[0].z=-.16;for(let i=0;i<6;i++)r=readCrop();assert.equal(r.move,1);crop[0].z=.16;for(let i=0;i<6;i++)r=readCrop();assert.equal(r.move,-1);crop[0].z=0;for(let i=0;i<6;i++)r=readCrop();assert.equal(r.move,0);
crop[0].visibility=.1;assert.equal(readCrop().valid,false);assert.equal(c.walk,0);
console.log('PASS camera-depth punches/retraction, arm following, guard hold, gentle torso movement, cropped hips, missing hands, neutral stop and tracking-loss reset');
