// NODE_PATH=/path/to/node_modules node test_ui_v25.cjs
const {JSDOM}=require('jsdom'),fs=require('fs'),assert=require('assert');
const html=fs.readFileSync(__dirname+'/templates/index.html','utf8').replace(/<script[\s\S]*?<\/script>/g,'');
const code=f=>fs.readFileSync(__dirname+'/static/'+f,'utf8');
function env(){const d=new JSDOM(html,{url:'https://fitness.example',runScripts:'outside-only',pretendToBeVisual:true});const w=d.window;w.Headers=Headers;w.Request=Request;w.Response=Response;w.I18N={lang:'en'};return {d,w}}
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
(async()=>{
 const {d,w}=env();let sessions=0,profiles=0,stops=0;
 w.fetch=async(path,opt={})=>{
  if(path==='/session'){sessions++;if(sessions===1)throw Error('temporary offline');return json({session_token:'token-'+sessions,guest:false,email:'member@example.com'})}
  if(path==='/profiles'){profiles++;return profiles===1?json({session_expired:true},401):json({profiles:[{id:7,name:'Saved player'}]})}
  if(path==='/stop'){stops++;return json({session_expired:true},401)}
  return json({error:'Sign in'},401);
 };
 w.eval(code('account-ui.js'));const response=await w.fetch('/profiles');assert.equal(response.status,200);assert.equal((await response.json()).profiles[0].id,7);assert.equal(sessions,3);assert.equal(profiles,2);assert.equal(w.FitnessAccount.email,'member@example.com');
 assert.equal((await w.fetch('/social/me')).status,401);assert.equal(sessions,3);
 assert.equal((await w.fetch('/stop',{method:'POST'})).status,401);assert.equal(stops,1);assert.equal(sessions,3);
 d.window.close();console.log('PASS: failed bootstrap recovers; expired GET session reconnects; account retained; writes never replayed');
 for(const stall of ['headers','body']){
  const {d,w}=env();w.$=id=>w.document.getElementById(id);w.accountText=(th,en)=>en;w.fitnessToken='test';w.coachRevision=0;w.isSecureContext=true;w.requestAnimationFrame=()=>1;w.cancelAnimationFrame=()=>{};w.HTMLMediaElement.prototype.play=async()=>{};w.HTMLMediaElement.prototype.pause=()=>{};
  w.HTMLCanvasElement.prototype.getContext=()=>new Proxy({},{get:()=>()=>{}});w.HTMLCanvasElement.prototype.toBlob=fn=>fn(new w.Blob(['frame']));
  Object.defineProperties(w.HTMLVideoElement.prototype,{readyState:{get:()=>3},videoWidth:{get:()=>640},videoHeight:{get:()=>480}});
  Object.defineProperty(w.navigator,'mediaDevices',{value:{getUserMedia:async()=>({getTracks:()=>[{stop(){}}],getVideoTracks:()=>[{readyState:'live',stop(){}}]})}});
  w.fetch=async()=>stall==='headers'?new Promise(()=>{}):({ok:true,json:()=>new Promise(()=>{})});w.originalFetch=w.fetch;
  const timer=w.setTimeout.bind(w);w.setTimeout=(fn,ms,...args)=>timer(fn,ms===10000?5:ms,...args);
  w.eval(code('session-camera.js')+'\nwindow.cameraTest=BrowserCamera;');await w.cameraTest.open();w.fitnessState={running:true,set_id:'set'};w.cameraTest.start();await new Promise(r=>setTimeout(r,30));assert(w.cameraFailure.includes('timed out'),stall);assert(w.cameraTest.active);w.cameraTest.close();d.window.close();
 }
 console.log('PASS: stalled frame headers and stalled JSON body both time out without closing the live camera');
})().catch(e=>{console.error(e);process.exit(1)});
