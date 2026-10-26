'use strict';
const BrowserCamera=(()=>{
 let video=document.createElement('video');video.muted=true;video.autoplay=true;video.playsInline=true;
 video.setAttribute('playsinline','');video.setAttribute('webkit-playsinline','');
 video.id='liveVideo';video.className='live-video';video.hidden=true;document.querySelector('.screen').prepend(video);
 const drawing=document.createElement('canvas');drawing.id='poseDrawing';drawing.className='pose-drawing';document.querySelector('.screen').append(drawing);const draw=drawing.getContext('2d');let landmarks=[],handLandmarks=[],pointsAt=0,raf=0;
 const pairs=[[11,12],[11,13],[13,15],[12,14],[14,16],[11,23],[12,24],[23,24],[23,25],[25,27],[24,26],[26,28]];
 const fingers=[[0,1,2,3,4],[0,5,6,7,8],[5,9,10,11,12],[9,13,14,15,16],[13,17,18,19,20],[0,17]];
 function paint(){if(!stream)return;if(drawing.width!==(video.videoWidth||640))drawing.width=video.videoWidth||640;if(drawing.height!==(video.videoHeight||480))drawing.height=video.videoHeight||480;draw.clearRect(0,0,drawing.width,drawing.height);if(performance.now()-pointsAt<350&&landmarks.length){draw.strokeStyle='#7be9b2';draw.fillStyle='#fff';draw.lineWidth=3;for(const [a,b] of pairs){if((window.fitnessState?.focus!=='full')&&(a>24||b>24))continue;const p=landmarks[a],q=landmarks[b];if(p?.[2]>.5&&q?.[2]>.5){draw.beginPath();draw.moveTo(p[0]*drawing.width,p[1]*drawing.height);draw.lineTo(q[0]*drawing.width,q[1]*drawing.height);draw.stroke()}}}if(performance.now()-pointsAt<650){draw.strokeStyle='#ffd66b';draw.lineWidth=2;for(const hand of handLandmarks)for(const chain of fingers){draw.beginPath();chain.forEach((id,i)=>{const p=hand[id];if(p)(i?draw.lineTo(p[0]*drawing.width,p[1]*drawing.height):draw.moveTo(p[0]*drawing.width,p[1]*drawing.height))});draw.stroke()}}raf=requestAnimationFrame(paint)}
 const canvas=document.createElement('canvas'),context=canvas.getContext('2d');
 let stream=null,generation=0,timer=null,imageURL=null,controller=null,failures=0,openedAt=0,opening=false,activeSet=null;
 function report(message){window.cameraFailure=message;document.getElementById('status').textContent=message;console.warn('[45 Fitness camera]',message)}
 function stopCurrent(){const id=activeSet||window.fitnessState?.set_id;return fetch('/stop',{method:'POST',headers:id?{'X-Set-ID':id}:{}})}
 function close(){window.LocalPose?.close();window.latestFrameState=null;opening=false;activeSet=null;generation++;cancelAnimationFrame(raf);video.hidden=true;landmarks=[];draw.clearRect(0,0,drawing.width,drawing.height);clearTimeout(timer);if(controller)controller.abort();controller=null;if(stream)stream.getTracks().forEach(t=>{t.onended=null;t.stop()});stream=null;video.pause();video.srcObject=null;if(imageURL)URL.revokeObjectURL(imageURL);imageURL=null;}
 async function open(){
  clearTimeout(hiddenTimer);
  if(stream&&stream.getVideoTracks().some(t=>t.readyState==='live'))return false;
  close();opening=true;const mine=generation;
  const oldVideo=video;video=oldVideo.cloneNode(false);video.muted=true;video.autoplay=true;video.playsInline=true;oldVideo.replaceWith(video);
  if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia){close();throw Error('มือถือให้เปิดลิงก์ HTTPS จาก Start-Share.ps1 ก่อน จึงใช้กล้องได้')}
  try{
   const camera=Number(document.getElementById('camera').value);
   const constraints={audio:false,video:{facingMode:{ideal:camera===1?'environment':'user'},width:{ideal:640},height:{ideal:480},frameRate:{ideal:30,max:30}}};let granted;
   for(let attempt=0;attempt<4;attempt++){
    if(mine!==generation)throw Error('ยกเลิกเปิดกล้องแล้ว');
    try{
     let expired=false,deadline;const pending=navigator.mediaDevices.getUserMedia(attempt===3?{audio:false,video:true}:constraints);
     pending.then(value=>{if(expired||mine!==generation)value.getTracks().forEach(t=>t.stop())},()=>{});
     try{granted=await Promise.race([pending,new Promise((_,reject)=>{deadline=setTimeout(()=>{expired=true;reject(Error(accountText('รออนุญาตกล้องนานเกินไป กดรีเซ็ตแล้วลองใหม่','Camera permission timed out. Reset and retry.')))},25000)})])}finally{clearTimeout(deadline)}break
    }
    catch(error){if(!['NotReadableError','AbortError'].includes(error.name)||attempt===3)throw error;await new Promise(resolve=>setTimeout(resolve,[350,800,1500][attempt]));}
   }
   if(mine!==generation){granted.getTracks().forEach(t=>t.stop());throw Error('ยกเลิกเปิดกล้องแล้ว')}
   stream=granted;video.srcObject=stream;video.hidden=false;
   for(let attempt=0;;attempt++){try{let timer;try{await Promise.race([video.play(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Camera playback timed out')),8000)})])}finally{clearTimeout(timer)}break}catch(error){if(error.name!=='AbortError'||attempt>=2||mine!==generation)throw error;await new Promise(r=>setTimeout(r,150))}}
   if(mine!==generation)throw Error('ยกเลิกเปิดกล้องแล้ว');
   if(!stream.getVideoTracks().some(t=>t.readyState==='live'))throw Error('กล้องหยุดทำงานหลังเปิด กรุณาลองอีกครั้ง');
   video.style.transform=drawing.style.transform=camera===1?'none':'scaleX(-1)';video.hidden=false;document.getElementById('feed').hidden=true;document.getElementById('placeholder').hidden=true;document.getElementById('overlay').hidden=false;paint();
   for(const track of stream.getVideoTracks())track.onended=()=>{if(mine===generation){const stopping=stopCurrent();close();stopping.catch(()=>{});report('กล้องถูกอุปกรณ์ปิด กดรีเซ็ตกล้องแล้วเริ่มใหม่ / Camera ended; reset and start again')}};
   openedAt=Date.now();failures=0;window.LocalPose?.start();return true;
  }catch(error){if(mine===generation)close();const messages={NotAllowedError:'กรุณาอนุญาตกล้องใน Safari หรือ Chrome แล้วลองอีกครั้ง',NotFoundError:'ไม่พบกล้องในเครื่องนี้',NotReadableError:'กล้องถูกใช้อยู่ ลองปิดแอปอื่นที่ใช้กล้องก่อน'};throw Error(messages[error.name]||error.message)}
 }
 // Bound both the HTTP response and its body: a stalled status/body must not freeze the frame loop.
 async function cameraJSON(url,options={},timeoutMs=10000){
  const requestController=new AbortController();controller=requestController;let deadline;
  try{return await Promise.race([
   (async()=>{const response=await fetch(url,{...options,signal:requestController.signal});const data=await response.json();return {response,data}})(),
   new Promise((_,reject)=>{deadline=setTimeout(()=>{requestController.abort();reject(Error('Camera server timed out. Retrying / เซิร์ฟเวอร์ตอบช้า กำลังลองใหม่'))},timeoutMs)})
  ])}finally{clearTimeout(deadline);if(controller===requestController)controller=null}
 }
 async function frame(mine){
  if(mine!==generation||!stream)return;
  const state=window.fitnessState;
  if(!state?.running){if(Date.now()-openedAt<10000){timer=setTimeout(()=>frame(mine),200);return}close();return}
  const start=performance.now();
  try{
   if(video.readyState<2||!video.videoWidth){timer=setTimeout(()=>frame(mine),200);return}
   let response,result,local=false;
   if(window.LocalPose?.ready){
    try{const payload=await window.LocalPose.detect(video,!!state.grip_enabled);if(mine!==generation)return;
     const reply=await cameraJSON('/pose-frame',{method:'POST',headers:{'Content-Type':'application/json','X-Set-ID':state.set_id},body:JSON.stringify(payload)});
     response=reply.response;result=reply.data;local=true;
     if(!response.ok&&response.status!==409){window.LocalPose.disable();local=false}
    }catch(error){if(mine!==generation)return;window.LocalPose.disable()}
   }
   if(!local){
    const scale=Math.min(640/video.videoWidth,640/video.videoHeight,1);
    const width=Math.round(video.videoWidth*scale),height=Math.round(video.videoHeight*scale);
    if(canvas.width!==width)canvas.width=width;if(canvas.height!==height)canvas.height=height;
    context.drawImage(video,0,0,canvas.width,canvas.height);
    const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.75));
    if(mine!==generation)return;if(!blob)throw Error('Cannot capture camera frame');
    const reply=await cameraJSON('/frame',{method:'POST',headers:{'Content-Type':'image/jpeg','X-Set-ID':state.set_id,'X-Frame-Format':'landmarks'},body:blob});response=reply.response;result=reply.data;
   }
   if(mine!==generation)return;
   if(response.status===409){
    if(activeSet!==state.set_id){timer=setTimeout(()=>frame(mine),100);return}
    const {response:current,data:snapshot}=await cameraJSON('/status',{cache:'no-store'},5000);
    if(mine!==generation)return;
    if(current.ok&&snapshot.running){adopt(snapshot);timer=setTimeout(()=>frame(mine),100);return}
    close();report(accountText('เซตหยุดแล้ว กดรีเซ็ตกล้องเพื่อเริ่มใหม่','Workout stopped. Press Reset camera to start again.'));return;
   }
   if(!response.ok)throw Error(result?.error||'ส่งภาพไม่สำเร็จ');
   if(mine!==generation)return;if(activeSet!==state.set_id){timer=setTimeout(()=>frame(mine),50);return;}
   window.cameraFailure='';handLandmarks=result.hands||[];landmarks=result.landmarks||[];pointsAt=performance.now();failures=0;
   window.coachHands={count:handLandmarks.length,at:Date.now()};window.coachLandmarks={points:landmarks,at:Date.now(),mirrored:Number(document.getElementById('camera').value)!==1};
   window.latestFrameState={state:{...result.state,server_today:result.server_today},at:Date.now()};
   document.getElementById('captureInfo').textContent=(window.I18N?.lang==='en'?'Live camera · AI response ':'ภาพสด · ผลตรวจใช้เวลา ')+Math.round(performance.now()-start)+' ms';

  }catch(error){
   if(mine!==generation)return;
   failures++;report('กล้องของคุณ / Camera: '+error.message);
   if(failures>=8){const stopping=stopCurrent();close();stopping.catch(()=>{});return}
  }
  if(mine===generation)timer=setTimeout(()=>frame(mine),failures?Math.min(2000,250*failures):Math.max(25,80-(performance.now()-start)));
 }
 function start(){activeSet=window.fitnessState?.set_id;opening=false;clearTimeout(timer);openedAt=Date.now();frame(generation)}
 function observe(state){
  // Poll/cache data is not a camera shutdown command. Only explicit controls,
  // track end, or a current frame rejected by the server can end this stream.
  if(stream&&!opening&&activeSet&&(state.set_id!==activeSet||!state.running))return false;
  window.fitnessState=state;return true;
 }
 function adopt(state){window.latestFrameState=null;window.fitnessState=state;if(stream)activeSet=state.set_id;return true}
 return {open,close,start,observe,adopt,get opening(){return opening},get active(){return !!stream}};
})();
// Hidden/background tabs stop their own camera and voice, including on mobile lock.
function leaveWorkout(){window.coachRevision++;BrowserCamera.close();if(typeof cancelVoice==='function')cancelVoice();if(fitnessToken)originalFetch('/stop',{method:'POST',headers:{'X-Coach-Session':fitnessToken,...(window.fitnessState?.set_id?{'X-Set-ID':window.fitnessState.set_id}:{})},keepalive:true}).catch(()=>{});}
window.addEventListener('pagehide',leaveWorkout);
let hiddenTimer;
document.addEventListener('visibilitychange',()=>{clearTimeout(hiddenTimer);if(document.hidden&&!BrowserCamera.opening){const revision=window.coachRevision;hiddenTimer=setTimeout(()=>{if(document.hidden&&!BrowserCamera.opening&&revision===window.coachRevision)leaveWorkout()},15000)}});
window.addEventListener('pageshow',event=>{if(event.persisted)location.reload()});

document.getElementById('refreshApp').onclick=async()=>{BrowserCamera.close();if(typeof cancelVoice==='function')cancelVoice();try{await Promise.race([fetch('/stop',{method:'POST',headers:window.fitnessState?.set_id?{'X-Set-ID':window.fitnessState.set_id}:{}}),new Promise(r=>setTimeout(r,2500))])}finally{location.reload()}};
