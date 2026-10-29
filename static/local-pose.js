'use strict';
// Fail closed into the existing image pipeline; never creates a second camera stream.
window.LocalPose=(()=>{
 let worker=null,ready=false,disabled=false,serial=0,pending=null,initTimer=null;
 const fail=()=>{ready=false;disabled=true;clearTimeout(initTimer);worker?.terminate();worker=null;if(pending){clearTimeout(pending.timer);pending.reject(Error('Local pose unavailable'));pending=null}};
 function start(){if(worker||disabled||!window.Worker||!window.createImageBitmap)return;
  try{worker=new Worker('/static/pose-worker.js?v=42');worker.onerror=fail;
   worker.onmessage=({data})=>{if(data.type==='ready'){ready=true;clearTimeout(initTimer)}else if(data.type==='error')fail();else if(data.type==='result'&&pending&&data.id===pending.id){const p=pending;pending=null;clearTimeout(p.timer);p.resolve(data)}};
   initTimer=setTimeout(fail,45000);worker.postMessage({type:'init',model:new URL('/camera/pose-model?quality='+encodeURIComponent(window.fitnessState?.pose_quality||'lite'),location.href).href});
  }catch(e){fail()}
 }
 async function bitmap(video,options){let timer,expired=false;const task=createImageBitmap(video,options);task.then(image=>{if(expired)image.close()},()=>{});try{return await Promise.race([task,new Promise((_,reject)=>{timer=setTimeout(()=>{expired=true;reject(Error('Camera bitmap timeout'))},3000)})])}finally{clearTimeout(timer)}}
 async function detect(video,grip){if(!ready||pending)throw Error('Local pose not ready');const current=worker;const cap=window.fitnessState?.pose_quality==='full'?960:640;const scale=Math.min(cap/video.videoWidth,cap/video.videoHeight,1),image=await bitmap(video,{resizeWidth:Math.round(video.videoWidth*scale),resizeHeight:Math.round(video.videoHeight*scale)});if(!ready||worker!==current||pending){image.close();throw Error('Local pose closed')}
  return new Promise((resolve,reject)=>{const id=++serial;pending={id,resolve,reject,timer:setTimeout(fail,5000)};try{worker.postMessage({type:'frame',id,image,time:performance.now(),grip},[image])}catch(e){image.close();fail()}})
 }
 function close(){clearTimeout(initTimer);ready=false;worker?.terminate();worker=null;if(pending){clearTimeout(pending.timer);pending.reject(Error('Local pose closed'));pending=null}disabled=false}
 return{start,detect,close,restart(){close();start()},disable:fail,get ready(){return ready}};
})();
