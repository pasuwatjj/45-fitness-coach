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
   if(guard&&(guardSide==='both'||guardSide===side)){upper[0]*=.55;upper[1]=-.48;upper[2]=.86;lower[1]=.99;lower[2]=.12}
   if(guard&&guardSide!=='both'&&guardSide!==side){upper[1]=-.94;upper[2]=.35;lower[1]=.55;lower[2]=.75}
   if(m.kick&&m.active&&sign===m.sign){upper[0]+=sign*.4*m.lift;upper[1]-=.1*m.lift;lower[1]-=.4*m.lift}
   out[side]={upper,lower};
  }return out;
 }
 return {sample,arms,smooth};
})();
