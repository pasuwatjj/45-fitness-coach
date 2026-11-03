const fs=require('fs'),vm=require('vm'),assert=require('assert');
const doc=new EventTarget(),win=new EventTarget(),saved=new Map();doc.closest=()=>null;doc.hidden=false;let now=1000,enabled=true;
const sandbox={window:win,document:doc,AbortController,performance:{now:()=>now},localStorage:{getItem:k=>saved.get(k),setItem:(k,v)=>saved.set(k,v)}};win.I18N={lang:'en'};vm.runInNewContext(fs.readFileSync('static/boxing-motion.js','utf8'),sandbox);sandbox.BoxingMotion=win.BoxingMotion;vm.runInNewContext(fs.readFileSync('static/boxing-computer.js','utf8'),sandbox);sandbox.BoxingKeys=win.BoxingKeys;
const c=new win.BoxingComputer(()=>enabled),key=(code,type='keydown',repeat=false)=>{const e=new Event(type,{cancelable:true});Object.assign(e,{code,repeat,ctrlKey:false,altKey:false,metaKey:false});doc.dispatchEvent(e);return e};
key('KeyW');key('KeyA');assert.equal(c.read(now).move,1);assert.equal(c.read(now).strafe,1);
key('ControlLeft');assert(c.read(now).dash);now+=80;key('ControlLeft','keydown',true);assert(!c.read(now).dash);key('ControlLeft','keyup');now+=100;key('ControlLeft');assert(!c.read(now).dash);key('ControlLeft','keyup');now+=700;key('ControlLeft');assert(c.read(now).dash);key('ControlLeft','keyup');
now+=200;key('KeyQ');assert.equal(c.read(now).action,'control');key('KeyQ','keyup');assert.equal(c.read(now).action,'left');now+=210;const p=c.read(now);assert.equal(p.action,'control');assert(p.posture.turn<-.2);key('KeyQ','keydown',true);assert.equal(c.read(now).action,'control');key('KeyQ','keyup');now+=500;key('KeyI');let kick=c.read(now);assert.equal(kick.action,'right');assert.equal(kick.punchType,'kick');
key('KeyC');assert(c.read(now).crouch>.5);key('KeyF');assert(c.read(now).guard);win.dispatchEvent(new Event('blur'));const stopped=c.read(now);assert.equal(stopped.move,0);assert.equal(stopped.strafe,0);assert(!stopped.guard);assert.equal(stopped.action,'control');
assert.equal(win.BoxingKeys.set('punchLeft','KeyW'),'duplicate');assert.equal(win.BoxingKeys.set('punchLeft','Escape'),'invalid');assert.equal(win.BoxingKeys.set('punchLeft','KeyJ'),null);now+=800;key('KeyQ');assert.equal(c.read(now).action,'control');key('KeyJ');key('KeyJ','keyup');assert.equal(c.read(now).action,'left');assert(win.BoxingKeys.hint().includes('J/E'));
enabled=false;key('KeyW');assert(!c.read(now).valid);enabled=true;assert.equal(c.read(now).move,0);c.destroy();console.log('PASS WASD/diagonals, Ctrl dash edge and cooldown, Q/E fists, U/I kicks, C crouch, F guard, no key-repeat strikes, blur cleanup and persisted unique remaps');

// Every combination hit requires a distinct press. Baseline stance is visual, never free evasion.
enabled=true;const combo=new win.BoxingComputer(()=>enabled);now+=1000;
const tap=code=>{key(code);key(code,'keyup');return combo.read(now)};
assert.equal(tap('KeyJ').punchType,'straight');now+=430;assert.equal(tap('KeyE').punchType,'straight');now+=430;assert.equal(tap('KeyJ').punchType,'hook');now+=430;
assert.equal(tap('KeyU').punchType,'kick');key('KeyW');assert.equal(combo.read(now+280).move,0);now+=500;assert.equal(tap('KeyE').action,'control');now+=270;assert.equal(tap('KeyE').action,'right');
now+=500;combo.reset();let idle=combo.read(now);assert.equal(idle.bend,0);assert.equal(idle.crouch,0);key('KeyW');key('ControlLeft');let duck=combo.read(now);assert(duck.dash&&duck.dashVisualUntil>now);assert.equal(duck.crouch,0);key('ControlLeft','keyup');key('KeyW','keyup');
enabled=false;for(const k of Object.values(win.BoxingKeys.bindings))key(k);assert.equal(combo.read(now).valid,false);enabled=true;assert.equal(combo.read(now).action,'control');assert.equal(combo.read(now).move,0);combo.destroy();
for(const type of ['straight','hook','uppercut','kick'])for(const hand of ['left','right']){const duration=type==='kick'?760:480;let previous=win.BoxingMotion.sample(type,hand,0);for(let ms=1;ms<=duration;ms++){let m=win.BoxingMotion.sample(type,hand,ms);for(const k of ['reach','lift','turn','hipTurn','lean','roll','duck'])assert(Math.abs(m[k]-previous[k])<.025);previous=m}assert.equal(previous.reach,0);assert.equal(previous.lift,0)}
console.log('PASS three presses / three strikes, alternating hook, kick recovery, movement lock, visual-only idle/dash posture, all keys disabled outside computer mode, continuous choreography');

// New attack chords and directional defense (remapped left punch remains J).
now+=1000;const advanced=new win.BoxingComputer(()=>enabled);const press=(code,ctrlKey=false)=>{const e=new Event('keydown',{cancelable:true});Object.assign(e,{code,repeat:false,ctrlKey,altKey:false,metaKey:false});doc.dispatchEvent(e);return e};
press('ControlLeft',true);assert(press('KeyW',true).defaultPrevented);assert(advanced.read(now).dash);key('KeyW','keyup');key('ControlLeft','keyup');now+=700;
key('Space');key('KeyA');let upperLeft=advanced.read(now);assert.equal(upperLeft.action,'left');assert.equal(upperLeft.punchType,'uppercut');assert.equal(upperLeft.strafe,0);assert(!upperLeft.dash);key('KeyA','keyup');now+=450;key('KeyD');const upperRight=advanced.read(now);assert.equal(upperRight.action,'right');assert.equal(upperRight.punchType,'uppercut');key('KeyD','keyup');key('Space','keyup');now+=450;
key('KeyW');key('Space');let upper=advanced.read(now);assert.equal(upper.punchType,'uppercut');assert.equal(upper.action,'right');assert.equal(upper.move,0);key('KeyW','keyup');key('Space','keyup');now+=450;
key('KeyF');key('KeyJ');let guard=advanced.read(now);assert.equal(guard.guardSide,'left');assert.equal(guard.action,'control');key('KeyE');assert.equal(advanced.read(now).guardSide,'both');key('KeyJ','keyup');assert.equal(advanced.read(now).guardSide,'right');key('KeyE','keyup');assert.equal(advanced.read(now).guardSide,'both');key('KeyF','keyup');assert.equal(advanced.read(now).guardSide,null);advanced.destroy();
const old={...win.BoxingKeys.bindings,dash:'Space'};delete old.special;const legacyStore=new Map([['45-boxing-keys-v1',JSON.stringify(old)]]),migration={window:{I18N:{lang:'en'}},localStorage:{getItem:k=>legacyStore.get(k)||null,setItem:(k,v)=>legacyStore.set(k,v)}};vm.runInNewContext(fs.readFileSync('static/boxing-computer.js','utf8'),migration);assert.equal(migration.window.BoxingKeys.bindings.dash,'ControlLeft');assert.equal(migration.window.BoxingKeys.bindings.special,'Space');assert.equal(migration.window.BoxingKeys.bindings.punchLeft,'KeyJ');
console.log('PASS real Ctrl modifier handling, Space-direction uppercuts in either key order, one strike per chord, no chord movement, directional/both guard without punches, and persisted v1 migration');
// A confirmed parry permits one recovery-cancel counter, not repeated local grants.
now+=1000;const parrier=new win.BoxingComputer(()=>true);assert(parrier.attack('left','straight',now));parrier.lastDash=now;now+=40;
assert(!parrier.attack('right','straight',now));parrier.grantCounter(123,650);assert(parrier.attack('right','straight',now));assert.equal(parrier.lastDash,now-40);parrier.grantCounter(123,600);assert(!parrier.attack('left','straight',now));
now+=1000;parrier.grantCounter(124,20);now+=21;parrier.lastStrike=now;assert(!parrier.attack('left','straight',now));parrier.destroy();
console.log('PASS one immediate parry counter, duplicate grant protection and counter expiry');

// Guard snapshots may arrive during a remote punch: preserve extension, then recover smoothly.
for(const type of ['straight','hook','uppercut'])for(const hand of ['left','right']){
 let old=null;for(let ms=0;ms<=480;ms++){const m=win.BoxingMotion.sample(type,hand,ms);m.type=type;const arms=win.BoxingMotion.arms(m,true,'both');
  if(ms===180){const free=win.BoxingMotion.arms(m,false);assert.deepEqual(arms[hand],free[hand]);}
  if(old)for(const side of ['left','right'])for(const part of ['upper','lower'])for(let i=0;i<3;i++)assert(Math.abs(arms[side][part][i]-old[side][part][i])<.05);
  old=arms;
 }
}
console.log('PASS committed punches retain full extension through guard snapshots and recover continuously');

// A real-time minute at 40% speed advances 24 seconds of punch/cooldown animation.
now+=1000;const clockStart=win.BoxingMotion.now();win.BoxingMotion.setSpeed(.4,now+60000);now+=1000;assert(Math.abs(win.BoxingMotion.now()-clockStart-400)<1e-6);now+=59000;assert(Math.abs(win.BoxingMotion.now()-clockStart-24000)<1e-6);assert.equal(win.BoxingMotion.speed,1);now+=500;assert(Math.abs(win.BoxingMotion.now()-clockStart-24500)<1e-6);
const skillControls=new win.BoxingComputer(()=>true);key('KeyV');assert(skillControls.read(win.BoxingMotion.now()).skill);key('KeyV','keydown',true);assert(!skillControls.read(win.BoxingMotion.now()).skill);key('KeyV','keyup');skillControls.destroy();
console.log('PASS continuous shared slow clock, exact real-time expiry and one skill per V press');
const legacyKeys={...win.BoxingKeys.bindings};delete legacyKeys.skill;legacyKeys.punchLeft='KeyV';saved.set('45-boxing-keys-v2',JSON.stringify(legacyKeys));vm.runInNewContext(fs.readFileSync('static/boxing-computer.js','utf8'),sandbox);assert.equal(win.BoxingKeys.bindings.punchLeft,'KeyV');assert.notEqual(win.BoxingKeys.bindings.skill,'KeyV');assert.equal(new Set(Object.values(win.BoxingKeys.bindings)).size,Object.keys(win.BoxingKeys.bindings).length);console.log('PASS saved key remaps survive skill binding migration, including an existing V binding');

const xControls=new win.BoxingComputer(()=>true);key(win.BoxingKeys.bindings.ruesi);assert(xControls.read(now).ruesi);key(win.BoxingKeys.bindings.ruesi,'keydown',true);assert(!xControls.read(now).ruesi);key(win.BoxingKeys.bindings.ruesi,'keyup');xControls.destroy();
const beforeX={...win.BoxingKeys.bindings};delete beforeX.ruesi;beforeX.slipRight='KeyX';saved.set('45-boxing-keys-v2',JSON.stringify(beforeX));vm.runInNewContext(fs.readFileSync('static/boxing-computer.js','utf8'),sandbox);assert.equal(win.BoxingKeys.bindings.ruesi,'KeyX');assert.equal(win.BoxingKeys.bindings.slipRight,'KeyB');assert.equal(win.BoxingKeys.bindings.punchLeft,beforeX.punchLeft);assert.equal(new Set(Object.values(win.BoxingKeys.bindings)).size,Object.keys(win.BoxingKeys.bindings).length);console.log('PASS one X special per press and non-destructive X/B saved-key migration');

// Holding is a windup; only release commits a normal punch. Cancelled holds never fire.
sandbox.BoxingKeys=win.BoxingKeys;now+=2000;const chargeControl=new win.BoxingComputer(()=>enabled);win.BoxingKeys.reset();
key('KeyQ');assert.equal(chargeControl.read(now).action,'control');now+=1500;
let charging=chargeControl.read(now);assert.equal(charging.chargeHand,'left');assert.equal(charging.chargeProgress,1);assert.equal(charging.action,'control');
key('KeyQ','keyup');let charged=chargeControl.read(now);assert.equal(charged.action,'left');assert.equal(charged.chargeMultiplier,2);assert.equal(chargeControl.read(now).action,'control');
now+=600;key('KeyE');now+=1000;key('KeyF');key('KeyF','keyup');key('KeyE','keyup');assert.equal(chargeControl.read(now).action,'control');
now+=600;key('KeyQ');win.dispatchEvent(new Event('blur'));key('KeyQ','keyup');assert.equal(chargeControl.read(now).action,'control');
assert.equal(win.BoxingKeys.set('punchLeft','Mouse0'),null);assert.equal(win.BoxingKeys.set('punchRight','Mouse2'),null);assert.equal(win.BoxingKeys.set('dash','Mouse0'),'invalid');assert.equal(win.BoxingKeys.name('Mouse2'),'RMB');
const pointer=(type,button)=>{const e=new Event(type,{cancelable:true});Object.assign(e,{button,pointerType:'mouse'});doc.dispatchEvent(e);return e};
doc.closest=()=>({});pointer('pointerdown',0);now+=1500;assert.equal(chargeControl.read(now).chargeHand,'left');pointer('pointerup',0);assert.equal(chargeControl.read(now).chargeMultiplier,2);
now+=600;pointer('pointerdown',2);now+=60;pointer('pointerup',2);assert.equal(chargeControl.read(now).action,'right');assert(pointer('contextmenu',2).defaultPrevented);
now+=600;doc.closest=()=>null;pointer('pointerdown',0);pointer('pointerup',0);assert.equal(chargeControl.read(now).action,'control');
chargeControl.destroy();console.log('PASS charge release, full ×2 cap, guard/blur cancel, mouse remaps, right-click suppression only in arena, clicks outside arena ignored');

win.BoxingKeys.reset();now+=2000;const energyControl=new win.BoxingComputer(()=>true);
for(let i=0;i<10;i++){now+=500;assert(energyControl.attack('left','straight',win.BoxingMotion.playerNow()));energyControl.read(win.BoxingMotion.playerNow())}
assert.equal(energyControl.stamina,0);now+=500;assert(!energyControl.attack('right','straight',win.BoxingMotion.playerNow()));
energyControl.setCombat(5,480);assert(!energyControl.attack('right','straight',win.BoxingMotion.playerNow()));
key('KeyF');key('KeyS');key('ControlLeft');const escape=energyControl.read(win.BoxingMotion.playerNow());assert(escape.guard&&escape.dash&&escape.move===-1);key('KeyF','keyup');key('KeyS','keyup');key('ControlLeft','keyup');
now+=500;energyControl.setCombat(5);assert(energyControl.attack('right','straight',win.BoxingMotion.playerNow()));energyControl.destroy();
console.log('PASS ten punches exhaust 20 stamina, empty and hit-stun block attacks, guard + dash escape stays available, recovery unlocks punches');
