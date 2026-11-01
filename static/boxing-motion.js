'use strict';
// Shared strike choreography for computer controls and camera-triggered assisted strikes.
window.BoxingMotion=(()=>{
 const smooth=x=>{x=Math.max(0,Math.min(1,x));return x*x*(3-2*x)},ramp=(t,a,b)=>smooth((t-a)/(b-a));
 function sample(type,hand,ms){
  const kick=type==='kick',sign=hand==='left'?1:-1,active=ms>=0&&ms<(kick?760:480);
  const reach=active?ramp(ms,kick?140:55,kick?280:180)*(1-ramp(ms,kick?330:205,kick?540:360)):0;
  const lift=kick&&active?ramp(ms,0,170)*(1-ramp(ms,510,760)):0;
  const load=active?ramp(ms,0,55)*(1-ramp(ms,55,180)):0;
  const turn=kick?-sign*(.7*lift+.25*reach):-sign*(.36*reach-.10*load);
  return {active,kick,sign,reach,load,lift,turn,hipTurn:kick?turn*.85:turn*.65,duck:type==='uppercut'?.60*load+.10*reach:0,lean:kick?-.72*lift:type==='uppercut'?.48*load-.12*reach:0,roll:kick?sign*.28*lift:type==='uppercut'?sign*(.14*load-.10*reach):0};
 }
 function arms(m,guard=false,guardSide='both'){
  const out={};for(const [side,sign]of [['left',1],['right',-1]]){
   const p=m.active&&!m.kick&&sign===m.sign?m.reach:0,hook=m.type==='hook',uppercut=m.type==='uppercut';
   const upper=[sign*(.13*(1-p)+(hook?.65:-.18)*p),-.72*(1-p)+.04*p,.68+.32*p];
   const lower=[-sign*(.22*(1-p)+(hook?.95:.18)*p),.94*(1-p),.34+.66*p];
   // Chamber beside the ribs, then drive upward with a bent elbow and recover.
   if(uppercut&&m.active&&sign===m.sign){const load=m.load;upper[0]=sign*(.13-.07*p);upper[1]=-.72-.12*load+.82*p;upper[2]=.68-.15*load+.24*p;lower[0]=-sign*(.22-.14*p);lower[1]=.94-.70*load+.04*p;lower[2]=.34+.50*load-.16*p}
   // A newly received guard must not cut a committed punch off mid-extension.
   // Recover into guard as the fist returns; the other arm can guard throughout.
   if(guard){const weight=m.active&&!m.kick&&sign===m.sign?1-Math.max(m.reach,m.load||0):1,cover=guardSide==='both'||guardSide===side;
    const gu=cover?[upper[0]*.55,-.48,.86]:[upper[0],-.94,.35],gl=cover?[lower[0],.99,.12]:[lower[0],.55,.75];
    for(let i=0;i<3;i++){upper[i]+=(gu[i]-upper[i])*weight;lower[i]+=(gl[i]-lower[i])*weight}
   }
   if(m.kick&&m.active&&sign===m.sign){upper[0]+=sign*.4*m.lift;upper[1]-=.1*m.lift;lower[1]-=.4*m.lift}
   out[side]={upper,lower};
  }return out;
 }
 return {sample,arms,smooth};
})();
