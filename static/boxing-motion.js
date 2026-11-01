'use strict';
// Computer choreography only. Tracking continues to use measured joint directions.
window.BoxingMotion=(()=>{
 const smooth=x=>{x=Math.max(0,Math.min(1,x));return x*x*(3-2*x)},ramp=(t,a,b)=>smooth((t-a)/(b-a));
 function sample(type,hand,ms){
  const kick=type==='kick',sign=hand==='left'?1:-1,active=ms>=0&&ms<(kick?760:480);
  const reach=active?ramp(ms,kick?140:55,kick?280:180)*(1-ramp(ms,kick?330:205,kick?540:360)):0;
  const lift=kick&&active?ramp(ms,0,170)*(1-ramp(ms,510,760)):0;
  const load=active?ramp(ms,0,55)*(1-ramp(ms,55,180)):0;
  const turn=kick?-sign*(.7*lift+.25*reach):-sign*(.36*reach-.10*load);
  return {active,kick,sign,reach,lift,turn,hipTurn:kick?turn*.85:turn*.65,lean:kick?-.72*lift:0,roll:kick?sign*.28*lift:0};
 }
 function arms(m,guard=false){
  const out={};for(const [side,sign]of [['left',1],['right',-1]]){
   const p=m.active&&!m.kick&&sign===m.sign?m.reach:0,hook=m.type==='hook';
   const upper=[sign*(.13*(1-p)+(hook?.65:-.18)*p),-.72*(1-p)+.04*p,.68+.32*p];
   const lower=[-sign*(.22*(1-p)+(hook?.95:.18)*p),.94*(1-p),.34+.66*p];
   if(guard&&!p){upper[0]*=.55;upper[1]=-.48;upper[2]=.86;lower[1]=.99;lower[2]=.12}
   if(m.kick&&m.active&&sign===m.sign){upper[0]+=sign*.4*m.lift;upper[1]-=.1*m.lift;lower[1]-=.4*m.lift}
   out[side]={upper,lower};
  }return out;
 }
 return {sample,arms,smooth};
})();
