/* RPG-only muscle deformation of the approved Quaternius mesh.
   Measurements set overall fullness separately; verified EXP supplies these levels. */
'use strict';
window.FitnessMuscleProgression=(()=>{
 const clamp=v=>Number.isFinite(v)?Math.max(0,Math.min(1,v)):0;
 const smooth=(a,b,v)=>{const t=clamp((v-a)/(b-a));return t*t*(3-2*t)};
 function development(growth={}){
  const g=growth.levels||{},s=growth.arm_levels||{};
  return Object.fromEntries(['chest','back','legs','shoulders','left','right'].map(k=>[k,clamp(k==='left'||k==='right'?(s[k]??g.arms):g[k])]));
 }
 function deform(x,y,z,height,g){
  const h=y/height,ax=Math.abs(x),side=x>=0?'left':'right';
  if(h>.86)return {position:[x,y,z],detail:1}; // face/hair remain untouched
  const limb=smooth(.18,.255,ax);
  const arms=limb*smooth(.42,.50,h)*(1-smooth(.76,.82,h));
  const legs=(1-smooth(.23,.29,ax))*smooth(.04,.15,h)*(1-smooth(.48,.57,h));
  const shoulders=smooth(.11,.20,ax)*smooth(.72,.78,h)*(1-smooth(.81,.86,h));
  const torso=(1-limb)*smooth(.52,.62,h)*(1-smooth(.77,.85,h));
  const front=smooth(-.025,.035,z),chest=torso*front,back=torso*(1-front);
  const armCenter=Math.sign(x)*(.212+(1.455-y)*.268);
  const armScale=1-arms*.22*(1-g[side]);
  x=armCenter+(x-armCenter)*armScale;z=-.04+(z+.04)*armScale;
  const legCenter=Math.sign(x)*.114,legScale=1-legs*.18*(1-g.legs);
  x=legCenter+(x-legCenter)*legScale;z=-.035+(z+.035)*legScale;
  x*=1-shoulders*.08*(1-g.shoulders);
  z*=1-chest*.25*(1-g.chest)-back*.20*(1-g.back);
  // Hand/foot/neck detail stays authored. Baked muscle shadows and normals fade
  // independently over the same smooth anatomical regions as mesh development.
  const coverage=Math.max(arms,legs,shoulders,torso);
  const total=arms+legs+shoulders+chest+back;
  const amount=total?(arms*g[side]+legs*g.legs+shoulders*g.shoulders+chest*g.chest+back*g.back)/total:0;
  return {position:[x,y,z],detail:1-coverage+coverage*amount};
 }
 return {development,deform};
})();
