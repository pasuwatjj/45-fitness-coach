// Regression checks for hung network responses and request ownership.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(__dirname+'/static/session-camera.js','utf8');
const helper=source.slice(source.indexOf(' async function cameraJSON('),source.indexOf(' async function frame('));
(async()=>{
 let mode='ok',activeSignal;
 const ctx=vm.createContext({AbortController,setTimeout,clearTimeout,fetch:async(url,options)=>{
  activeSignal=options.signal;const requestMode=mode;
  if(requestMode==='headers')return new Promise(()=>{});
  return {ok:true,json:async()=>requestMode==='body'?new Promise(()=>{}):{running:true}};
 }});
 vm.runInContext('let controller=null;'+helper+';this.request=cameraJSON;this.getController=()=>controller;',ctx);
 const good=await ctx.request('/status',{},50);assert.equal(good.data.running,true);assert.equal(ctx.getController(),null);
 for(const scenario of ['headers','body']){mode=scenario;await assert.rejects(ctx.request('/status',{},20),/timed out/);assert(activeSignal.aborted);assert.equal(ctx.getController(),null)}
 mode='body';const previous=ctx.request('/frame',{},20);mode='ok';const newer=ctx.request('/status',{},50);await newer;await assert.rejects(previous,/timed out/);assert.equal(ctx.getController(),null);
 console.log('PASS: successful response, stalled headers, stalled body, cleanup and overlapping request ownership');
})().catch(e=>{console.error(e);process.exit(1)});
