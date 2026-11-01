'use strict';
window.BoxingKeys=(()=>{
 const defaults={left:'KeyA',right:'KeyD',forward:'KeyW',back:'KeyS',punchLeft:'KeyQ',punchRight:'KeyE',kickLeft:'KeyU',kickRight:'KeyI',dash:'ControlLeft',special:'Space',guard:'KeyF',crouch:'KeyC',slipLeft:'KeyZ',slipRight:'KeyX',leanBack:'KeyR'};
 const labels={left:['เดินซ้าย','Move left'],right:['เดินขวา','Move right'],forward:['เดินหน้า','Move forward'],back:['ถอยหลัง','Move back'],punchLeft:['ต่อย / กันซ้ายพร้อมการ์ด','Left punch / left guard'],punchRight:['ต่อย / กันขวาพร้อมการ์ด','Right punch / right guard'],kickLeft:['เตะซ้าย','Left kick'],kickRight:['เตะขวา','Right kick'],dash:['แดชพร้อมปุ่มเดิน','Dash + movement'],special:['อัปเปอร์คัตพร้อมทิศทาง','Uppercut + direction'],guard:['ยกการ์ด (กดค้าง)','Guard (hold)'],crouch:['ย่อตัว','Crouch'],slipLeft:['หลบซ้าย','Slip left'],slipRight:['หลบขวา','Slip right'],leanBack:['เอนหลัง','Lean back']};
 const valid=code=>/^(Key[A-Z]|Digit[0-9]|Space|ShiftLeft|ShiftRight|ControlLeft|ControlRight)$/.test(code),name=code=>code==='Space'?'SPACE':code.replace('Key','').replace('Digit','').replace('ShiftLeft','L SHIFT').replace('ShiftRight','R SHIFT').replace('ControlLeft','CTRL').replace('ControlRight','R CTRL');
 const complete=saved=>saved&&Object.keys(saved).length===Object.keys(defaults).length&&Object.keys(defaults).every(k=>valid(saved[k]))&&new Set(Object.values(saved)).size===Object.keys(defaults).length;
 let bindings={...defaults};try{const saved=JSON.parse(localStorage.getItem('45-boxing-keys-v2'));if(complete(saved))bindings=saved;else{const old=JSON.parse(localStorage.getItem('45-boxing-keys-v1'));if(old&&Object.keys(defaults).filter(k=>k!=='special').every(k=>valid(old[k]))&&new Set(Object.values(old)).size===Object.keys(old).length){const candidate={...defaults,...old,dash:'ControlLeft',special:'Space'};for(const k of Object.keys(candidate))if(!['dash','special'].includes(k)&&['Space','ControlLeft'].includes(candidate[k]))candidate[k]=defaults[k];if(complete(candidate))bindings=candidate}}}catch{}
 const save=()=>{try{localStorage.setItem('45-boxing-keys-v2',JSON.stringify(bindings))}catch{}};save();
 const hint=()=>{const group=keys=>keys.map(k=>name(bindings[k])).join('/');return group(['forward','left','back','right'])+(window.I18N?.lang==='en'?' move · ':' เดิน · ')+group(['punchLeft','punchRight'])+(window.I18N?.lang==='en'?' punch · ':' ต่อย · ')+name(bindings.dash)+(window.I18N?.lang==='en'?' dash · ':' แดช · ')+name(bindings.special)+' + '+group(['left','right','forward'])+(window.I18N?.lang==='en'?' uppercut':' อัปเปอร์คัต')};
 return{defaults,labels,valid,hint,name,get bindings(){return{...bindings}},set(action,code){if(!(action in defaults)||!valid(code))return'invalid';if(Object.entries(bindings).some(([k,v])=>k!==action&&v===code))return'duplicate';bindings[action]=code;save();return null},reset(){bindings={...defaults};save()}};
})();
window.BoxingComputer=class{
 constructor(enabled){this.enabled=enabled;this.keys=new Set();this.lastStrike=-1000;this.lastDash=-1000;this.dashUsed=false;this.specialUsed=false;this.strike=null;this.pending=null;this.combo=0;this.comboHand=null;this.events=new AbortController();const signal=this.events.signal;
  document.addEventListener('keydown',e=>{if(!this.enabled()||e.altKey||e.metaKey||e.target.closest('input,select,textarea,[contenteditable=true]'))return;const bindings=BoxingKeys.bindings,action=Object.keys(bindings).find(k=>bindings[k]===e.code);if(!action)return;
   // Ctrl is gameplay only for its bound modifier and directional dash chords.
   if(e.ctrlKey&&!e.code.startsWith('Control')&&!(this.on('dash')&&(['left','right','forward','back'].includes(action)||(performance.now()<(this.counterUntil||0)&&(action.startsWith('punch')||action==='special')))))return;
   e.preventDefault();if(e.repeat||this.keys.has(e.code))return;this.keys.add(e.code);const now=performance.now();
   if(action==='guard'){this.combo=0;this.comboHand=null;this.pending=null}
   if(this.on('guard'))return;
   if(this.on('special')){this.specialStrike(now);return}
   if(/^(punch|kick)/.test(action)){const kick=action.startsWith('kick'),hand=action.endsWith('Left')?'left':'right';this.attack(hand,kick?'kick':'straight',now,!kick)}
  },{signal});
  document.addEventListener('keyup',e=>{this.keys.delete(e.code);if(e.code===BoxingKeys.bindings.dash)this.dashUsed=false;if(e.code===BoxingKeys.bindings.special||!['left','right','forward'].some(k=>this.on(k)))this.specialUsed=false},{signal});window.addEventListener('blur',()=>this.reset(),{signal});document.addEventListener('visibilitychange',()=>{if(document.hidden)this.reset()},{signal});
 }
 grantCounter(id,remaining){if(id!==this.counterGrant){this.counterGrant=id;this.counterUntil=performance.now()+Math.max(0,remaining)}}
 on(action){return this.keys.has(BoxingKeys.bindings[action])}
 attack(hand,type,now,chain=false){const counter=type!=='kick'&&now<(this.counterUntil||0);if((!counter&&(now-this.lastStrike<(this.lastStrikeType==='kick'?760:420)||now-this.lastDash<180))||this.on('guard'))return false;if(counter){this.counterUntil=0;this.dashCancelled=true;}
  this.combo=chain&&now-this.lastStrike<720&&hand!==this.comboHand?this.combo+1:1;if(chain&&this.combo===3)type='hook';this.comboHand=chain?hand:null;if(!chain||this.combo===3)this.combo=0;
  this.lastStrike=now;this.lastStrikeType=type;this.strike={hand,type,at:now};this.pending=this.strike;return true;
 }
 specialStrike(now){if(this.specialUsed||this.on('guard')||(this.on('dash')&&now>=(this.counterUntil||0)))return;const directions=['left','right','forward'].filter(k=>this.on(k));if(directions.length!==1)return;this.specialUsed=true;const d=directions[0];this.attack(d==='left'?'left':'right','uppercut',now)}
 reset(){this.counterUntil=0;this.keys.clear();this.strike=null;this.pending=null;this.dashUsed=false;this.specialUsed=false;this.combo=0;this.comboHand=null}
 read(now){if(!this.enabled()){this.reset();return{valid:false,action:'idle',label:''}}const on=k=>this.on(k),guard=on('guard'),left=on('punchLeft'),right=on('punchRight'),guardSide=guard?(left!==right?(left?'left':'right'):'both'):null;
  const strike=this.strike,m=BoxingMotion.sample(strike?.type,strike?.hand,strike?now-strike.at:1000);m.type=strike?.type;const arms=BoxingMotion.arms(m,guard,guardSide);for(const arm of Object.values(arms))for(const key of ['upper','lower']){const n=Math.hypot(...arm[key]);arm[key]=arm[key].map(v=>v/n)}
  const pending=guard?null:this.pending;this.pending=null;const locked=m.active&&m.kick,special=on('special'),move=locked||special?0:Number(on('forward'))-Number(on('back')),strafe=locked||special?0:Number(on('left'))-Number(on('right'));let dash=false;if(!on('dash'))this.dashUsed=false;else if((move||strafe)&&!this.dashUsed){this.dashUsed=true;if(now-this.lastDash>=650){dash=true;this.lastDash=now;this.dashCancelled=false}}
  return{valid:true,action:pending?.hand||'control',punchType:pending?.type||'straight',arms,posture:{turn:m.turn,hipTurn:m.hipTurn,tilt:0,headPitch:0,headYaw:-m.turn*.5,headRoll:0},move,strafe,dash,guard,guardSide,dashVisualUntil:this.dashCancelled?0:this.lastDash+180,crouch:on('crouch')?.75:0,slip:(Number(on('slipLeft'))-Number(on('slipRight')))*.8,bend:on('leanBack')?-.45:on('crouch')?.5:0,label:guard?(window.I18N?.lang==='en'?'Guard · '+guardSide:'การ์ด · '+({left:'ซ้าย',right:'ขวา',both:'สองแขน'}[guardSide])):window.I18N?.lang==='en'?'Ready · Computer controls':'พร้อม · ควบคุมด้วยคอม'};
 }
 destroy(){this.reset();this.events.abort()}
};
