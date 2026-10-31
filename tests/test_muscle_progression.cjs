'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
global.window={};vm.runInThisContext(fs.readFileSync('static/muscle-progression.js','utf8'));
const {development,deform}=window.FitnessMuscleProgression;
const zero=development(),full=development({levels:{arms:1,chest:1,back:1,legs:1,shoulders:1},arm_levels:{left:1,right:1}});
const cases={left:[.32,1.2,.04],right:[-.32,1.2,.04],chest:[.07,1.3,.12],back:[.07,1.3,-.12],legs:[.17,.6,.07],shoulders:[.23,1.45,-.04]};
for(const [group,p] of Object.entries(cases)){
 const result=[];for(const amount of [0,.5,.8,1])result.push(deform(...p,1.81,{...zero,[group]:amount}));
 assert(result[0].position.some((v,i)=>Math.abs(v-result[3].position[i])>.005),group+' should visibly grow');
 assert(result[0].detail<result[3].detail,group+' detail should grow');
 const distances=result.map(r=>Math.hypot(...r.position.map((v,i)=>v-result[0].position[i])));
 assert(distances.every((v,i)=>!i||v>=distances[i-1]-1e-9),group+' monotone');
 const head=[.04,1.7,.10];assert.deepEqual(deform(...head,1.81,{...zero,[group]:1}).position,head);
}
assert.deepEqual(deform(...cases.right,1.81,{...zero,left:1}),deform(...cases.right,1.81,zero));
assert.deepEqual(deform(...cases.legs,1.81,{...zero,chest:1}),deform(...cases.legs,1.81,zero));
assert.deepEqual(deform(...cases.chest,1.81,{...zero,back:1}),deform(...cases.chest,1.81,zero));
assert.equal(development({levels:{legs:NaN,chest:Infinity,back:-4},arm_levels:{left:99}}).left,1);
for(const gender of ['male','female']){
 const assets=JSON.parse(fs.readFileSync('static/models/quaternius/'+gender+'.json'));
 const height=Math.max(...assets.find(m=>m.name.includes('Super')).position.filter((_,i)=>i%3===1));
 for(const mesh of assets)for(const data of [mesh,...Object.values(mesh.clothing||{})]){
  for(let i=0;i<data.position.length;i+=3)for(const g of [zero,full]){
   const p=data.position.slice(i,i+3),v=deform(...p,height,g);
   assert(v.position.every(Number.isFinite));assert(v.detail>=0&&v.detail<=1.000001);
   if(g===full)assert(v.position.every((n,j)=>Math.abs(n-p[j])<1e-9),'max development preserves approved geometry');
  }
 }
}
console.log('PASS: independent groups/sides, monotone growth, unchanged face, bounded values, original max geometry, finite body/clothing vertices');
