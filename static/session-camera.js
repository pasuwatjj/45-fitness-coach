'use strict';
const BrowserCamera=(()=>{
 let video=document.createElement('video');video.muted=true;video.autoplay=true;video.playsInline=true;
 video.setAttribute('playsinline','');video.setAttribute('webkit-playsinline','');
 video.id='liveVideo';video.className='live-video';video.hidden=true;document.querySelector('.screen').prepend(video);
 const drawing=document.createElement('canvas');drawing.id='poseDrawing';drawing.className='pose-drawing';document.querySelector('.screen').append(drawing);const draw=drawing.getContext('2d');let peoplePoints=[],landmarks=[],handLandmarks=[],pointsAt=0,raf=0,visible=[];
 const pairs=[[11,12],[11,13],[13,15],[12,14],[14,16],[11,23],[12,24],[23,24],[23,25],[25,27],[24,26],[26,28]];
 const fingers=[[0,1,2,3,4],[0,5,6,7,8],[5,9,10,11,12],[9,13,14,15,16],[13,17,18,19,20],[0,17]];
 let drawingScale=1,lastLayout=-Infinity;
 function layoutDrawing(){
  const now=performance.now();if(now-lastLayout<200)return;lastLayout=now;
  const w=video.videoWidth||640,h=video.videoHeight||480;
  const rect=window.PoseDrawing.contentRect(video.clientWidth,video.clientHeight,w,h);
  drawingScale=rect.scale;
  drawing.style.inset='auto';drawing.style.left=(video.offsetLeft+rect.x)+'px';drawing.style.top=(video.offsetTop+rect.y)+'px';
  drawing.style.width=rect.width+'px';drawing.style.height=rect.height+'px';
 }
 const resizeDrawing=()=>{lastLayout=-Infinity};
 window.addEventListener('resize',resizeDrawing);document.addEventListener('fullscreenchange',resizeDrawing);
 function paint(){
  if(!stream)return;if(performance.now()-lastMetrics>=500)metrics();
  if(drawing.width!==(video.videoWidth||640))drawing.width=video.videoWidth||640;
  if(drawing.height!==(video.videoHeight||480))drawing.height=video.videoHeight||480;
  layoutDrawing();draw.clearRect(0,0,drawing.width,drawing.height);
  const age=performance.now()-pointsAt;draw.globalAlpha=Math.max(0,Math.min(1,(650-age)/150));
  const options={width:drawing.width,height:drawing.height,scale:drawingScale,full:window.fitnessState?.focus==='full'};
  if(age<650&&landmarks.length)window.PoseDrawing.paint(draw,landmarks,{...options,visible});
  if(age<650)for(const person of peoplePoints){
   const body=person.landmarks;if(!body.length)continue;
   const color=(window.PersonTracking?.colors||['#7be9b2','#8bc8ff'])[person.player_id-1];
   window.PoseDrawing.paint(draw,body,{...options,color});
   const head=body[11];if(head&&head[2]>.5){draw.save();draw.translate(head[0]*drawing.width,head[1]*drawing.height-18/drawingScale);if(Number(document.getElementById('camera').value)!==1)draw.scale(-1,1);draw.font='bold '+(18/drawingScale)+'px sans-serif';draw.fillStyle=color;draw.fillText('P'+person.player_id,0,0);draw.restore()}
  }
  if(age<650){draw.strokeStyle='#ffd66b';draw.lineWidth=2/Math.max(.15,drawingScale);for(const hand of handLandmarks)for(const chain of fingers){draw.beginPath();chain.forEach((id,i)=>{const p=hand[id];if(p)(i?draw.lineTo(p[0]*drawing.width,p[1]*drawing.height):draw.moveTo(p[0]*drawing.width,p[1]*drawing.height))});draw.stroke()}}
  draw.globalAlpha=1;raf=requestAnimationFrame(paint);
 }
 const canvas=document.createElement('canvas'),context=canvas.getContext('2d');
 let stream=null,generation=0,timer=null,imageURL=null,controller=null,failures=0,openedAt=0,opening=false,activeSet=null;
 let localTimer=null,localTask=null,localSample=null,lastSentSample=null,frameBusy=false,revision=0;
 const fpsSelect=document.getElementById('detectionFps'),fpsInfo=document.getElementById('detectionFpsInfo');
 const cameraFpsSelect=document.getElementById('cameraFps');
 let cameraFpsChoice='auto';
 try{const saved=localStorage.getItem('45fitness.cameraFps');if(['auto','30','60'].includes(saved))cameraFpsChoice=saved}catch(e){}
 cameraFpsSelect.value=cameraFpsChoice;
 cameraFpsSelect.onchange=()=>{cameraFpsChoice=['auto','30','60'].includes(cameraFpsSelect.value)?cameraFpsSelect.value:'auto';cameraFpsSelect.value=cameraFpsChoice;try{localStorage.setItem('45fitness.cameraFps',cameraFpsChoice)}catch(e){};metrics()};
 let fpsChoice='auto',cost=80,detectionTimes=[],cameraTimes=[],cameraCallback=null,lastMetrics=0;
 try{const saved=localStorage.getItem('45fitness.detectionFps');if(['auto','10','15','20','30'].includes(saved))fpsChoice=saved}catch(e){}
 fpsSelect.value=fpsChoice;
 fpsSelect.onchange=()=>{fpsChoice=['auto','10','15','20','30'].includes(fpsSelect.value)?fpsSelect.value:'auto';try{localStorage.setItem('45fitness.detectionFps',fpsChoice)}catch(e){};detectionTimes=[];metrics()};
 function interval(){return fpsChoice==='auto'?Math.max(1000/30,cost*1.15):1000/Number(fpsChoice)}
 function measured(times,now){while(times.length&&now-times[0]>2000)times.shift();return times.length>1?(times.length-1)*1000/(times[times.length-1]-times[0]):0}
 function metrics(){const now=performance.now(),en=window.I18N?.lang==='en';fpsInfo.textContent=(en?'Detection actual: ':'ตรวจจับจริง: ')+measured(detectionTimes,now).toFixed(1)+' FPS · '+(en?'Camera actual: ':'กล้องจริง: ')+(video.requestVideoFrameCallback?measured(cameraTimes,now).toFixed(1):'—')+' FPS';document.getElementById('detectionFpsLabel').textContent=en?'Detection FPS limit':'จำกัด FPS ตรวจจับ';fpsSelect.options[0].textContent=en?'Auto (adaptive)':'อัตโนมัติ (ปรับตามเครื่อง)';document.getElementById('detectionFpsNote').textContent=en?'Maximum rate, not guaranteed. Actual detection depends on device / server speed.':'เป็นเพดาน ไม่รับประกัน FPS จริง ขึ้นกับความเร็วเครื่อง / เซิร์ฟเวอร์';document.getElementById('cameraFpsLabel').textContent=en?'Camera FPS preference':'FPS กล้องที่ต้องการ';cameraFpsSelect.options[0].textContent=en?'Auto (prefer 60 FPS)':'อัตโนมัติ (60 FPS)';document.getElementById('cameraFpsNote').textContent=en?'Applies next time the camera opens. 60 FPS depends on camera / browser support; lower rates are allowed. Detection remains limited to 30 FPS.':'ใช้เมื่อเปิดกล้องครั้งถัดไป 60 FPS ขึ้นกับกล้อง / เบราว์เซอร์ หากไม่รองรับใช้ค่าที่ต่ำกว่าได้ การตรวจจับยังจำกัดสูงสุด 30 FPS';lastMetrics=now}
 function detected(){detectionTimes.push(performance.now());metrics()}
 function trackCamera(mine){if(!video.requestVideoFrameCallback)return;cameraCallback=video.requestVideoFrameCallback(()=>{if(mine!==generation||!stream)return;cameraTimes.push(performance.now());measured(cameraTimes,performance.now());trackCamera(mine)})}
 metrics();
 if(window.I18N?.lang==='en'){document.getElementById('initialCameraHint').textContent='Open the camera with your selected shoulder, elbow and wrist visible.';document.getElementById('initialCountHint').textContent='Once your joints are visible, move from the starting position.'}
 // Display owns no counters. Coordinates always come from the current observation;
 // confidence hysteresis only keeps a currently observed joint visible near 0.5.
 const poseStability=new PoseStability();
 function showPoints(body,hands,at,wallAt,world=[]){
  body=poseStability.apply(body,at,(video.videoWidth||640)/(video.videoHeight||480));
  const st=window.fitnessState,tracking=st?.tracking?.status?.[0];
  const canHold=st?.running&&!st.paused&&st.person_count===1&&tracking!=='ambiguous'&&tracking!=='lost';
  if(!body.length&&canHold&&landmarks.length&&at-pointsAt<250){
   window.coachHands={count:0,at:wallAt};return;
  }
  const previous=at-pointsAt<650?visible:[];
  landmarks=body;handLandmarks=hands;pointsAt=at;
  visible=body.map((p,i)=>!!p&&Number.isFinite(p[0])&&Number.isFinite(p[1])&&p[2]>(previous[i] ? .45 : .5));
  window.coachHands={count:hands.length,at:wallAt};
  window.coachLandmarks={points:body,world,aspect:(video.videoWidth||640)/(video.videoHeight||480),at:wallAt,set_id:window.fitnessState?.set_id,mirrored:Number(document.getElementById('camera').value)!==1};
 }
 function resetPoints(){poseStability.reset();revision++;detectionTimes=[];localSample=null;lastSentSample=null;peoplePoints=[];landmarks=[];handLandmarks=[];visible=[];pointsAt=0;window.coachHands=null;window.coachLandmarks=null;draw.clearRect(0,0,drawing.width,drawing.height)}
 function localTick(mine){
  if(mine!==generation||!stream||localTask)return;
  clearTimeout(localTimer);
  const state=window.fitnessState;
  if(!window.LocalPose?.ready||!state?.running||video.readyState<2){localTimer=setTimeout(()=>localTick(mine),80);return}
  const set=state.set_id,rev=revision,at=performance.now(),wallAt=Date.now();
  const task=(async()=>{
   try{
    const payload=await window.LocalPose.detect(video,!!state.grip_enabled);
    if(mine!==generation||!stream||revision!==rev||activeSet!==set||window.fitnessState?.set_id!==set)return;
    cost=cost*.75+(performance.now()-at)*.25;detected();localSample={payload,set,at,wallAt,completedAt:performance.now()};
    const matched=window.PersonTracking?.match(payload,window.fitnessState)||[];
    peoplePoints=state.person_count>1?matched:[];
    const freeCardio=state.cardio&&!state.tracking?.pinned?.[0];
    const body=freeCardio?(payload.pose||[]).map(p=>[p.x,p.y,p.visibility??0]):state.person_count>1?[]:(matched[0]?.landmarks||[]);
    showPoints(body,body.length&&(payload.poses||[]).length===1?(payload.hands||[]).map(hand=>hand.map(p=>[p.x,p.y])):[],performance.now(),Date.now(),freeCardio?(payload.world||[]).map(p=>[p.x,p.y,p.z]):matched[0]?.world||[]);
   }catch(error){if(mine===generation&&revision===rev){localSample=null;window.LocalPose?.disable()}}
  })();
  localTask=task;
  task.finally(()=>{if(localTask===task)localTask=null;if(mine===generation&&stream)localTimer=setTimeout(()=>localTick(mine),Math.max(0,interval()-(performance.now()-at)))});
 }
 function report(message){window.cameraFailure=message;document.getElementById('status').textContent=message;console.warn('[45 Fitness camera]',message)}
 function stopCurrent(){const id=activeSet||window.fitnessState?.set_id;return fetch('/stop',{method:'POST',headers:id?{'X-Set-ID':id}:{}})}
 function close(){if(cameraCallback!==null)video.cancelVideoFrameCallback?.(cameraCallback);cameraCallback=null;cameraTimes=[];window.LocalPose?.close();window.latestFrameState=null;opening=false;activeSet=null;generation++;clearTimeout(localTimer);localTask=null;frameBusy=false;resetPoints();cancelAnimationFrame(raf);video.hidden=true;landmarks=[];draw.clearRect(0,0,drawing.width,drawing.height);clearTimeout(timer);if(controller)controller.abort();controller=null;if(stream)stream.getTracks().forEach(t=>{t.onended=null;t.stop()});stream=null;video.pause();video.srcObject=null;if(imageURL)URL.revokeObjectURL(imageURL);imageURL=null;window.LiveAvatar?.sync();}
 async function open(){
  clearTimeout(hiddenTimer);
  if(opening)return false;
  if(stream&&stream.getVideoTracks().some(t=>t.readyState==='live'))return false;
  close();opening=true;const mine=generation;
  const oldVideo=video;video=oldVideo.cloneNode(false);video.muted=true;video.autoplay=true;video.playsInline=true;oldVideo.replaceWith(video);
  if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia){close();throw Error('มือถือให้เปิดลิงก์ HTTPS จาก Start-Share.ps1 ก่อน จึงใช้กล้องได้')}
  try{
   if(!window.PoseDrawing||!window.PersonTracking)throw Error(accountText('ไฟล์อัปเดตกล้องไม่ครบ กรุณาอัปโหลดไฟล์ static และ templates ให้ครบ แล้วรีโหลดหน้าเว็บ','Camera update files are missing. Upload all static and templates files, then reload.'));
   const camera=Number(document.getElementById('camera').value);
   const constraints={audio:false,video:{facingMode:{ideal:camera===1?'environment':'user'},width:{ideal:window.fitnessState?.pose_quality==='full'?1280:640},height:{ideal:window.fitnessState?.pose_quality==='full'?720:480},frameRate:cameraFpsChoice==='30'?{ideal:30,max:30}:{ideal:60,max:60}}};let granted,relaxed=false;
   for(let attempt=0;attempt<4;attempt++){
    if(mine!==generation)throw Error('ยกเลิกเปิดกล้องแล้ว');
    try{
     let expired=false,deadline;const pending=navigator.mediaDevices.getUserMedia(attempt===3?{audio:false,video:true}:relaxed?{audio:false,video:{facingMode:constraints.video.facingMode,width:constraints.video.width,height:constraints.video.height}}:constraints);
     pending.then(value=>{if(expired||mine!==generation)value.getTracks().forEach(t=>t.stop())},()=>{});
     try{granted=await Promise.race([pending,new Promise((_,reject)=>{deadline=setTimeout(()=>{expired=true;reject(Error(accountText('รออนุญาตกล้องนานเกินไป กดรีเซ็ตแล้วลองใหม่','Camera permission timed out. Reset and retry.')))},25000)})])}finally{clearTimeout(deadline)}break
    }
    catch(error){if(error.name==='OverconstrainedError'&&!relaxed&&attempt<3){relaxed=true;continue}if(!['NotReadableError','AbortError'].includes(error.name)||attempt===3)throw error;await new Promise(resolve=>setTimeout(resolve,[350,800,1500][attempt]));}
   }
   if(mine!==generation){granted.getTracks().forEach(t=>t.stop());throw Error('ยกเลิกเปิดกล้องแล้ว')}
   stream=granted;video.srcObject=stream;video.hidden=false;lastLayout=-Infinity;
   for(let attempt=0;;attempt++){try{let timer;try{await Promise.race([video.play(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Camera playback timed out')),8000)})])}finally{clearTimeout(timer)}break}catch(error){if(error.name!=='AbortError'||attempt>=2||mine!==generation)throw error;await new Promise(r=>setTimeout(r,150))}}
   if(mine!==generation)throw Error('ยกเลิกเปิดกล้องแล้ว');
   if(!stream.getVideoTracks().some(t=>t.readyState==='live'))throw Error('กล้องหยุดทำงานหลังเปิด กรุณาลองอีกครั้ง');
   video.style.transform=drawing.style.transform=camera===1?'none':'scaleX(-1)';video.hidden=false;document.getElementById('feed').hidden=true;document.getElementById('placeholder').hidden=true;document.getElementById('overlay').hidden=false;paint();
   for(const track of stream.getVideoTracks())track.onended=()=>{if(mine===generation){const stopping=stopCurrent();close();stopping.catch(()=>{});report('กล้องถูกอุปกรณ์ปิด กดรีเซ็ตกล้องแล้วเริ่มใหม่ / Camera ended; reset and start again')}};
   trackCamera(mine);openedAt=Date.now();failures=0;window.LocalPose?.start();return true;
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
 async function frameWork(mine){
  if(mine!==generation||!stream)return;
  const state=window.fitnessState;
  if(!state?.running){if(Date.now()-openedAt<10000){timer=setTimeout(()=>frame(mine),200);return}close();return}
  const start=performance.now(),rev=revision;
  try{
   if(video.readyState<2||!video.videoWidth){timer=setTimeout(()=>frame(mine),200);return}
   let response,result,local=false,capturedAt=performance.now(),capturedWallAt=Date.now();
   if(window.LocalPose?.ready){
    const sample=localSample;
    if(!sample||sample.set!==state.set_id||sample===lastSentSample||performance.now()-sample.completedAt>=650){timer=setTimeout(()=>frame(mine),50);return}
    lastSentSample=sample;
    const reply=await cameraJSON('/pose-frame',{method:'POST',headers:{'Content-Type':'application/json','X-Set-ID':state.set_id},body:JSON.stringify(sample.payload)});
    if(mine!==generation||revision!==rev)return;response=reply.response;result=reply.data;local=true;
    if(!response.ok&&response.status!==409){window.LocalPose.disable();localSample=null;local=false}
   }
   if(!local){
    if(mine!==generation||revision!==rev)return;
    capturedAt=performance.now();capturedWallAt=Date.now();
    const cap=state.pose_quality==='full'?960:640;const scale=Math.min(cap/video.videoWidth,cap/video.videoHeight,1);
    const width=Math.round(video.videoWidth*scale),height=Math.round(video.videoHeight*scale);
    if(canvas.width!==width)canvas.width=width;if(canvas.height!==height)canvas.height=height;
    context.drawImage(video,0,0,canvas.width,canvas.height);
    const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.75));
    if(mine!==generation||revision!==rev)return;if(!blob)throw Error('Cannot capture camera frame');
    const reply=await cameraJSON('/frame',{method:'POST',headers:{'Content-Type':'image/jpeg','X-Set-ID':state.set_id,'X-Frame-Format':'landmarks'},body:blob});response=reply.response;result=reply.data;
   }
   if(mine!==generation||revision!==rev)return;
   if(response.status===409){
    if(activeSet!==state.set_id){timer=setTimeout(()=>frame(mine),100);return}
    const {response:current,data:snapshot}=await cameraJSON('/status',{cache:'no-store'},5000);
    if(mine!==generation||revision!==rev)return;
    if(current.ok&&snapshot.running){adopt(snapshot);timer=setTimeout(()=>frame(mine),100);return}
    close();report(accountText('เซตหยุดแล้ว กดรีเซ็ตกล้องเพื่อเริ่มใหม่','Workout stopped. Press Reset camera to start again.'));return;
   }
   if(!response.ok)throw Error(result?.error||'ส่งภาพไม่สำเร็จ');
   if(mine!==generation||revision!==rev)return;if(activeSet!==state.set_id){timer=setTimeout(()=>frame(mine),50);return;}
   window.cameraFailure='';failures=0;
   if(!local&&!window.LocalPose?.ready){peoplePoints=result.players||[];cost=cost*.75+(performance.now()-start)*.25;detected();showPoints(result.landmarks||[],result.hands||[],capturedAt,capturedWallAt,result.world||[]);}
   window.latestFrameState={state:{...result.state,server_today:result.server_today},at:Date.now()};
   document.getElementById('captureInfo').textContent=(window.I18N?.lang==='en'?'Live camera · AI response ':'ภาพสด · ผลตรวจใช้เวลา ')+Math.round(performance.now()-start)+' ms';

  }catch(error){
   if(mine!==generation||revision!==rev)return;
   failures++;report('กล้องของคุณ / Camera: '+error.message);
   if(failures>=8){const stopping=stopCurrent();close();stopping.catch(()=>{});return}
  }
  if(mine===generation)timer=setTimeout(()=>frame(mine),failures?Math.min(2000,250*failures):Math.max(0,(window.LocalPose?.ready?80:interval())-(performance.now()-start)));
 }
 async function frame(mine){
  if(frameBusy||mine!==generation)return;
  frameBusy=true;try{await frameWork(mine)}finally{if(mine===generation){frameBusy=false;if(stream){clearTimeout(timer);timer=setTimeout(()=>frame(mine),failures?Math.min(2000,250*failures):Math.max(0,(window.LocalPose?.ready?80:interval())));}}}
 }
 function start(){if(activeSet!==window.fitnessState?.set_id)resetPoints();activeSet=window.fitnessState?.set_id;opening=false;clearTimeout(timer);openedAt=Date.now();localTick(generation);frame(generation)}
 function observe(state){
  // Poll/cache data is not a camera shutdown command. Only explicit controls,
  // track end, or a current frame rejected by the server can end this stream.
  if(stream&&!opening&&activeSet&&(state.set_id!==activeSet||!state.running))return false;
  window.fitnessState=state;return true;
 }
 function adopt(state){if(activeSet!==state.set_id)resetPoints();window.latestFrameState=null;window.fitnessState=state;if(stream)activeSet=state.set_id;return true}
 return {open,close,start,observe,adopt,clearPoints:resetPoints,get opening(){return opening},get active(){return !!stream}};
})();
// Hidden/background tabs stop their own camera and voice, including on mobile lock.
function leaveWorkout(){window.coachRevision++;BrowserCamera.close();if(typeof cancelVoice==='function')cancelVoice();if(fitnessToken)originalFetch('/stop',{method:'POST',headers:{'X-Coach-Session':fitnessToken,...(window.fitnessState?.set_id?{'X-Set-ID':window.fitnessState.set_id}:{})},keepalive:true}).catch(()=>{});}
window.addEventListener('pagehide',leaveWorkout);
let hiddenTimer;
document.addEventListener('visibilitychange',()=>{clearTimeout(hiddenTimer);if(document.hidden&&!BrowserCamera.opening){const revision=window.coachRevision;hiddenTimer=setTimeout(()=>{if(document.hidden&&!BrowserCamera.opening&&revision===window.coachRevision)leaveWorkout()},15000)}});
window.addEventListener('pageshow',event=>{if(event.persisted)location.reload()});

document.getElementById('refreshApp').onclick=async()=>{BrowserCamera.close();if(typeof cancelVoice==='function')cancelVoice();try{await Promise.race([fetch('/stop',{method:'POST',headers:window.fitnessState?.set_id?{'X-Set-ID':window.fitnessState.set_id}:{}}),new Promise(r=>setTimeout(r,2500))])}finally{location.reload()}};
