'use strict';
(()=>{
 const t=(th,en)=>window.I18N?.lang==='en'?en:th;
 const field=document.createElement('div');field.className='field';field.dataset.i18nIgnore='';field.style.cssText='max-width:100%;margin-top:8px';
 const label=document.createElement('label');label.htmlFor='poseQuality';const select=document.createElement('select');select.id='poseQuality';select.style.cssText='width:100%;max-width:100%;min-width:0';
 for(const value of ['lite','full']){const option=document.createElement('option');option.value=value;select.append(option)}
 let choice='full';try{const saved=localStorage.getItem('45fitness.poseQuality.v42');if(['lite','full'].includes(saved))choice=saved}catch(e){}select.value=choice;
 const note=document.createElement('p');note.className='note';note.dataset.i18nIgnore='';note.style.overflowWrap='anywhere';field.append(label,select,note);document.getElementById('cameraFps').parentElement.before(field);
 function render(){const state=window.fitnessState;select.disabled=!!state?.running||!!busy||BrowserCamera.opening;if(state?.running)select.value=state.pose_quality||'lite';else if(!select.disabled)select.value=choice;label.textContent=t('โมเดลตรวจจับท่า','Pose detection model');select.options[0].textContent=t('Lite · เร็วกว่า','Lite · faster');select.options[1].textContent=t('Full · โมเดลละเอียดขึ้น (ค่าเริ่มต้น)','Full · more detailed model (default)');note.textContent=t('ใช้เมื่อเปิดกล้องครั้งถัดไป Full อาจช้าลงและไม่รับประกันความแม่นยำ เส้นหนาและจุดสีช่วยมองเห็นตำแหน่งที่ตรวจพบ ไม่ใช่คะแนนฟอร์ม หากจุดคลาดให้เพิ่มแสง เห็นแขนและข้อมือครบ และลดการบังกัน','Applies next time the camera opens. Full may be slower and does not guarantee accuracy. Thick lines and colored dots show detected landmarks, not form scores. If joints drift, improve lighting, keep the whole arm and wrist visible, and reduce occlusion.')}
 select.onchange=()=>{choice=select.value;try{localStorage.setItem('45fitness.poseQuality.v42',choice)}catch(e){}render()};setInterval(render,350);render();
})();
