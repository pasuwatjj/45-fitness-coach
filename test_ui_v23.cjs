// Development regression tests: npm install jsdom in a separate tools folder;
// NODE_PATH=/path/to/node_modules node test_ui_v23.cjs
const {JSDOM}=require('jsdom'),fs=require('fs'),assert=require('assert');
const code=f=>fs.readFileSync(__dirname+'/static/'+f,'utf8');
function env(){const html=fs.readFileSync(__dirname+'/templates/index.html','utf8').replace(/<script[\s\S]*?<\/script>/g,'');const d=new JSDOM(html,{url:'https://fitness.example',runScripts:'outside-only',pretendToBeVisual:true});const w=d.window;w.$=id=>w.document.getElementById(id);w.I18N={lang:'en'};w.wasRunning=false;w.soundUserMuted=false;w.catalogById={};w.fitnessToken='token';w.coachRevision=0;w.cancelVoice=()=>{};w.accountText=(th,en)=>en;w.isSecureContext=true;w.requestAnimationFrame=()=>1;w.cancelAnimationFrame=()=>{};w.HTMLCanvasElement.prototype.getContext=()=>new Proxy({},{get:()=>()=>{}});w.HTMLMediaElement.prototype.play=async()=>{};w.HTMLMediaElement.prototype.pause=()=>{};w.URL.createObjectURL=()=> 'blob:mock';w.URL.revokeObjectURL=()=>{};return {d,w}}
(async()=>{
 const contexts=Array.from({length:3},env),tracks=[];
 for(const {w} of contexts){Object.defineProperty(w.navigator,'mediaDevices',{value:{getUserMedia:async()=>{const t={readyState:'live',stop(){this.readyState='ended'}};tracks.push(t);return {getTracks:()=>[t],getVideoTracks:()=>[t]}}}});w.fetch=async()=>({ok:true,json:async()=>({})});w.originalFetch=w.fetch;w.eval(code('session-camera.js')+'\nwindow.cameraTest=BrowserCamera;')}
 for(let i=0;i<200;i++){for(const {w} of contexts){assert(await w.cameraTest.open());assert(w.cameraTest.active);assert.equal(await w.cameraTest.open(),false)}contexts[0].w.cameraTest.close();assert(contexts[1].w.cameraTest.active);for(const {w} of contexts)w.cameraTest.close()}
 assert.equal(tracks.length,600);assert(tracks.every(t=>t.readyState==='ended'));contexts.forEach(x=>x.d.window.close());console.log('PASS: 3 browser contexts × 200 cycles, independent streams, all tracks released');
 for(const lang of ['th','en']){const {w,d}=env();w.I18N.lang=lang;const calls=[];w.FitnessAccount={guest:false};w.Community={refreshRole:()=>{}};w.setTab=()=>{w.ProfileDashboard.open()};w.post=async()=>({});w.loadProfiles=async()=>{};w.$('profile').onchange=()=>{};w.$('profile').append(new w.Option('Owner','1'));w.$('profile').value='1';
 const overview={profile:{id:2,name:'Shared member'},has_avatar:false,totals:{sets:0},streak:{current:2,best:3,completed:4},muscle_groups:[{group:'arms',sets:3,reps:25}],health:[],sets:[]};
 const progress={sets:[],days:[],comparisons:[],cardio:[{mode:'pushup',day:'2026-10-18',reps:5,duration:15,reps_per_minute:20,kcal:null,kind:'ranked'}]};
 w.fetch=async url=>{calls.push(url);return {ok:true,json:async()=>url==='/profiles'?{profiles:[{id:1,name:'Owner'}]}:url.endsWith('/progress')?progress:overview}};
 w.AngleHistory={mount:(p,id,shared)=>{assert(shared);calls.push('angles-shared')}};
 w.eval(code('charts.js'));w.eval(code('profile.js'));w.eval(code('progress.js'));await w.ProfileDashboard.openMember(2);await new Promise(r=>setTimeout(r,20));
 assert(calls.includes('/social/profiles/2/overview'));assert(calls.includes('/social/profiles/2/progress'));assert(calls.includes('angles-shared'));assert(w.document.querySelector('.donut-section svg'));assert.equal(w.document.querySelectorAll('#profilePage input[type=file]').length,0);assert.equal(w.$('profile').value,'1');assert(w.document.querySelector('.profile-tools').hidden);d.window.close();}
 console.log('PASS: TH/EN shared charts, read-only profile, no own-profile selection mutation');
})().catch(e=>{console.error(e);process.exit(1)});
(async()=>{
 for(const lang of ['th','en']){
  const {w,d}=env();w.I18N.lang=lang;w.busy=false;w.BrowserCamera={active:true,close(){}};w.action=async fn=>fn();const calls=[];w.post=async(u,data)=>{calls.push([u,data]);return {}};w.fetch=async()=>({ok:true,json:async()=>({players:[]})});w.enableSound=()=>{};w.unlockCoachAudio=()=>{};w.speak=()=>{};w.coinDing=()=>{};w.resetCamera=async()=>{};w.cancelControls=()=>{};w.$('profile').append(new w.Option('Player','1'));w.$('profile').value='1';w.eval(code('cardio.js'));
  const mode=w.document.querySelector('#cardioPage select');assert.equal(mode.value,'full');mode.value='pushup';mode.onchange();const allowance=w.document.querySelectorAll('#cardioPage select')[1];assert([...allowance.options].some(o=>o.value==='50'));allowance.value='50';assert(w.$('tolerance').querySelector('option[value="50"]'));const start=[...w.document.querySelectorAll('#cardioPage button')].find(b=>b.textContent.startsWith('▶'));await start.onclick();assert.equal(calls[0][0],'/cardio/start');assert.equal(calls[0][1].mode,'pushup');assert.equal(calls[0][1].tolerance,50);assert(w.$('cardioPage').textContent.includes(lang==='en'?'Knee push-ups':'วิดพื้นคุกเข่า'));d.window.close();
 }
 console.log('PASS: TH/EN push-up selector, tutorial and start payload');
 for(const lang of ['th','en']){
  const {w,d}=env();w.I18N.lang=lang;w.Headers=Headers;w.Request=Request;w.fetch=async()=>({ok:true,status:200,json:async()=>({session_token:'test',guest:true})});w.history.replaceState(null,'','#reset='+'a'.repeat(43));w.eval(code('account-ui.js'));assert.equal(w.location.hash,'');assert.equal(w.$('authPage').hidden,false);assert.equal(w.$('authRecovery').disabled,true);assert.equal(w.$('authConfirm').disabled,false);w.$('forgotPassword').click();assert.equal(w.$('authRecovery').disabled,true);assert.equal(w.$('authEmail').disabled,false);assert.equal(w.$('authPassword').disabled,true);await new Promise(r=>setTimeout(r,0));d.window.close();
 }
 console.log('PASS: emailed fragment opens reset form and clears URL; forgot flow asks email only');
})().catch(e=>{console.error(e);process.exit(1)});
