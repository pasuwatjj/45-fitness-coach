// v35: one inference at a time, CPU/WASM off the interface thread.
let pose,hands,busy=false,createPose=null,missingAt=null,lastReset=0;
self.onmessage=async({data})=>{
 if(data.type==='init'){
  try{
   const {FilesetResolver,PoseLandmarker,HandLandmarker}=await import('/static/vendor/mediapipe/vision_bundle.mjs');
   const files=await FilesetResolver.forVisionTasks('/static/vendor/mediapipe/wasm');
   createPose=()=>PoseLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:data.model},runningMode:'VIDEO',numPoses:3,minPoseDetectionConfidence:.6,minPosePresenceConfidence:.6,minTrackingConfidence:.6});
   pose=await createPose();
   try{hands=await HandLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:'/static/vendor/mediapipe/hand_landmarker.task'},runningMode:'VIDEO',numHands:2,minHandDetectionConfidence:.65,minTrackingConfidence:.65});}catch(e){hands=null}
   self.postMessage({type:'ready'});
  }catch(e){self.postMessage({type:'error',error:String(e)})}
  return;
 }
 if(data.type==='frame'){
  if(busy||!pose){data.image.close();return}busy=true;
  try{let p=pose.detectForVideo(data.image,data.time);let h=null;
   if(p.landmarks.length)missingAt=null;
   else{missingAt??=data.time;if(data.time-missingAt>2000&&data.time-lastReset>8000){
    lastReset=data.time;missingAt=data.time;pose.close();pose=await createPose();
    p=pose.detectForVideo(data.image,data.time+1);if(p.landmarks.length)missingAt=null;
   }}
   // Hand occlusion/failure must not discard a valid body-pose result.
   if(data.grip&&hands){try{h=hands.detectForVideo(data.image,data.time)}catch(e){h=null}}
   self.postMessage({type:'result',id:data.id,width:data.image.width,height:data.image.height,pose:p.landmarks[0]||[],world:p.worldLandmarks[0]||[],poses:p.landmarks,worlds:p.landmarks.map((_,i)=>p.worldLandmarks[i]||[]),hands:h?.landmarks||[],handWorld:h?.worldLandmarks||[]});
  }catch(e){self.postMessage({type:'error',error:String(e)})}finally{data.image.close();busy=false}
 }
};
