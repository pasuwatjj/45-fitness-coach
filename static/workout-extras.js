'use strict';
// Local-only conveniences: neither timer nor focus mode starts a workout.
(() => {
 const en=window.I18N&&I18N.lang==='en';
 const screen=document.querySelector('.screen'),rest=document.getElementById('restPanel');
 const score=document.createElement('div');score.id='cameraScore';score.className='screen-score';score.dataset.i18nIgnore='';
 const label=document.createElement('span');label.textContent=en?'Accepted reps':'ครั้งที่นับได้';
 const count=document.createElement('strong'),detail=document.createElement('small');count.textContent='0';score.append(label,count,detail);screen.append(score);
 setInterval(()=>{const s=window.fitnessState;if(!s)return;if(s.person_count>1){label.textContent=en?'Temporary · no saving':'เล่นชั่วคราว · ไม่บันทึก';count.textContent=(s.players||[]).map(p=>'P'+p.player_id+': '+p.reps).join(' · ');count.style.fontSize='clamp(18px,4vw,32px)';detail.textContent=en?'Stand apart · select again if lost':'ยืนแยกกัน · เลือกใหม่เมื่อหลุด';return}label.textContent=en?'Accepted reps':'ครั้งที่นับได้';count.style.fontSize='';count.textContent=s.reps||0;detail.textContent=(en?'Left ':'ซ้าย ')+(s.arms?.left?.reps??'—')+' · '+(en?'Right ':'ขวา ')+(s.arms?.right?.reps??'—')},150);
 const focus=document.createElement('button');focus.type='button';focus.className='secondary';
 focus.id='fullscreenWorkout';focus.textContent=en?'⛶ Large camera view':'⛶ ขยายภาพกล้อง';
 screen.before(focus);
 focus.onclick=async()=>{
  if(document.fullscreenElement){await document.exitFullscreen();return}
  if(screen.requestFullscreen){try{await screen.requestFullscreen();return}catch(e){}}
  screen.classList.toggle('focus-view');
 };
 const exit=document.createElement('button');exit.type='button';exit.className='focus-exit';
 exit.textContent=en?'Close large view':'ปิดภาพขยาย';
 exit.onclick=()=>{if(document.fullscreenElement)document.exitFullscreen();screen.classList.remove('focus-view')};screen.append(exit);
 const box=document.createElement('div');box.className='rest-timer';box.dataset.i18nIgnore='';
 const restLabel=document.createElement('label');restLabel.textContent=en?'Rest timer (seconds) ':'เวลาพัก (วินาที) ';
 const select=document.createElement('select');select.id='restDuration';
 for(const n of [30,45,60,90,120]){const o=document.createElement('option');o.value=String(n);o.textContent=String(n);select.append(o)}
 let duration=60;try{const saved=Number(localStorage.getItem('45-rest-seconds'));if([30,45,60,90,120].includes(saved))duration=saved}catch(e){}
 select.value=String(duration);restLabel.append(select);
 const output=document.createElement('output');output.id='restCountdown';output.setAttribute('aria-live','off');
 const reset=document.createElement('button');reset.type='button';reset.className='secondary';reset.textContent=en?'Restart timer':'เริ่มเวลาพักใหม่';
 box.append(restLabel,output,reset);rest.append(box);
 let end=0,key=null;
 function start(){end=Date.now()+duration*1000;draw()}
 function draw(){const left=Math.max(0,Math.ceil((end-Date.now())/1000));output.textContent=left?`${left} s`:en?'Ready? Start the next set when comfortable.':'พร้อมแล้วค่อยกดเริ่มเซตถัดไปนะ'}
 select.onchange=()=>{duration=Number(select.value);try{localStorage.setItem('45-rest-seconds',String(duration))}catch(e){}start()};reset.onclick=start;
 setInterval(()=>{const s=typeof lastState==='undefined'?null:lastState;if(!s||!s.paused){key=null;end=0;return}const next=s.set_id||'paused';if(key!==next){key=next;start()}draw()},250);
})();
