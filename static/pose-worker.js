// v35: one inference at a time, CPU/WASM off the interface thread.
let pose,hands,busy=false;
self.onmessage=async({data})=>{
 if(data.type==='init'){
  try{
   const {FilesetResolver,PoseLandmarker,HandLandmarker}=await import('/static/vendor/mediapipe/vision_bundle.mjs');
   const files=await FilesetResolver.forVisionTasks('/static/vendor/mediapipe/wasm');
   pose=await PoseLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:data.model},runningMode:'VIDEO',numPoses:1,minPoseDetectionConfidence:.6,minPosePresenceConfidence:.6,minTrackingConfidence:.6});
   try{hands=await HandLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:'/static/vendor/mediapipe/hand_landmarker.task'},runningMode:'VIDEO',numHands:2,minHandDetectionConfidence:.65,minTrackingConfidence:.65});}catch(e){hands=null}
   self.postMessage({type:'ready'});
  }catch(e){self.postMessage({type:'error',error:String(e)})}
  return;
 }
 if(data.type==='frame'){
  if(busy||!pose){data.image.close();return}busy=true;
  try{const p=pose.detectForVideo(data.image,data.time);let h=null;
   // Hand occlusion/failure must not discard a valid body-pose result.
   if(data.grip&&hands){try{h=hands.detectForVideo(data.image,data.time)}catch(e){h=null}}
   self.postMessage({type:'result',id:data.id,width:data.image.width,height:data.image.height,pose:p.landmarks[0]||[],world:p.worldLandmarks[0]||[],hands:h?.landmarks||[],handWorld:h?.worldLandmarks||[]});
  }catch(e){self.postMessage({type:'error',error:String(e)})}finally{data.image.close();busy=false}
 }
};
