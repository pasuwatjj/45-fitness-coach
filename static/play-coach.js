'use strict';
(() => {
 const en=window.I18N?.lang==='en',screen=document.querySelector('.screen');
 const info=document.createElement('p');info.className='hand-scan-note';info.setAttribute('role','status');info.dataset.i18nIgnore='';screen.after(info);
 const replay=document.createElement('button');replay.type='button';replay.className='secondary';
 replay.textContent=en?'▶ Hear the exercise instructions':'▶ ฟังวิธีจับและเล่นท่านี้';
 info.after(replay);
 replay.onclick=()=>{soundUserMuted=false;enableSound();unlockCoachAudio();$('voiceEnabled').checked=true;const ex=currentExercise();speak(ex.teaching,'teach_'+ex.id,true)};
 const hint=document.createElement('p');hint.className='note';hint.textContent=en?'With tutorial or coin sound enabled, Start enables audio. Mute with the sound button.':'เมื่อเลือกเสียงสอนหรือเสียงเหรียญ ปุ่มเริ่มจะเปิดเสียงให้ ปิดเสียงได้ที่ปุ่มเสียง';replay.after(hint);
 setInterval(()=>{
  if(!BrowserCamera.active){info.textContent=en?'Before starting, show your hands and upper body to the camera.':'ก่อนเริ่ม จัดกล้องให้เห็นมือและครึ่งตัวชัด ๆ';return}
  if(currentExercise().family!=='curl'||!$('gripEnabled').checked){info.textContent=en?'Detailed hand scan is available for Curl/Hammer with hand checks enabled.':'สแกนมือและนิ้วสำหรับ Curl/Hammer เมื่อเปิดดูการจับมือ';return}
  const h=window.coachHands;
  info.textContent=h&&Date.now()-h.at<1500&&h.count?(en?`Tracking ${h.count} hand(s), 21 points per hand. Yellow lines show fingers; grip is experimental, not certified.`:`พบมือ ${h.count} ข้าง · ติดตาม 21 จุดต่อมือ เส้นเหลืองคือแนวนิ้ว การจับเป็นการประเมินทดลอง`):(en?'Hand unclear: keep it in frame and well lit. Grip cannot be confirmed.':'มือยังไม่ชัด: จัดมือให้อยู่ในภาพและมีแสงพอ ยังยืนยันการจับไม่ได้');
 },700);
 window.spawnCoachCoins=(mode,result="accepted",label=null,difficulty=window.fitnessState?.difficulty||"beginner")=>{
  if(!BrowserCamera.active)return;
  const data=window.coachLandmarks,rect=screen.getBoundingClientRect(),video=document.getElementById('liveVideo');
  const vw=video.videoWidth||640,vh=video.videoHeight||480,scale=Math.min(rect.width/vw,rect.height/vh),w=vw*scale,h=vh*scale;
  for(const side of mode==='both'?['left','right']:[mode]){
   if(screen.querySelectorAll('.rep-coin').length>=8)break;
   const p=data&&Date.now()-data.at<1000?data.points[side==='left'?13:14]:null;
   const good=p&&p[2]>.65,x=good?(data.mirrored?1-p[0]:p[0]):.5,y=good?p[1]:.5;
   const coin=document.createElement('span');coin.className='rep-coin '+result;coin.setAttribute('aria-hidden','true');coin.textContent=label||(result==='rejected'?(en?'🔴 No count':'🔴 ไม่นับ'):result==='unverified'?(en?'⚪ Unclear':'⚪ รอตรวจ'):'🪙 +1');
   if(result==='accepted'){coin.replaceChildren();const disc=document.createElement('i');disc.className='training-coin '+difficulty;disc.textContent='45';const caption=document.createElement('b');caption.textContent=label||'+1';coin.append(disc,caption)}
   if(result==='rejected'){coin.replaceChildren();for(const half of ['left','right']){const shard=document.createElement('i');shard.className='coin-shard '+half;shard.textContent='🪙';coin.append(shard)}const caption=document.createElement('b');caption.textContent=en?'No count':'ไม่นับ';coin.append(caption)}
   coin.style.left=((rect.width-w)/2+x*w)+'px';coin.style.top=((rect.height-h)/2+y*h)+'px';screen.append(coin);
   coin.addEventListener('animationend',()=>coin.remove(),{once:true});setTimeout(()=>coin.remove(),1300);
  }
 };
})();

window.glassBreakSound=()=>{if(!soundEnabled||!audioContext||!$('coinEnabled').checked)return;try{const seconds=.3,buffer=audioContext.createBuffer(1,Math.floor(audioContext.sampleRate*seconds),audioContext.sampleRate),samples=buffer.getChannelData(0);for(let i=0;i<samples.length;i++)samples[i]=((Math.random()*2-1)*.65+Math.sin(i/audioContext.sampleRate*2*Math.PI*1537)*.16+Math.sin(i/audioContext.sampleRate*2*Math.PI*3121)*.16)*Math.pow(1-i/samples.length,3);const noise=audioContext.createBufferSource(),filter=audioContext.createBiquadFilter(),gain=audioContext.createGain();noise.buffer=buffer;filter.type='highpass';filter.frequency.value=1800;gain.gain.value=.12;noise.connect(filter);filter.connect(gain);gain.connect(audioContext.destination);noise.start();noise.onended=()=>{noise.disconnect();filter.disconnect();gain.disconnect()}}catch(e){}};
(()=>{const p=document.createElement('p');p.className='strict-counter-note';p.dataset.i18nIgnore='';document.querySelector('.screen').after(p);setInterval(()=>{const s=window.fitnessState;if(!s)return;p.textContent=window.I18N?.lang==='en'?`Not counted: ${s.rejected||0} form mismatches · ${s.unverified||0} unclear attempts. Speed alone is advice.`:`รอบที่ไม่นับเพราะต้องปรับฟอร์ม ${s.rejected||0} · ประเมินไม่ชัด ${s.unverified||0} · ความเร็วอย่างเดียวเป็นคำแนะนำ`},400)})();

(()=>{const b=document.createElement('button');b.type='button';b.className='secondary';b.dataset.i18nIgnore='';b.textContent=window.I18N?.lang==='en'?'🔊 Test broken-coin sound':'🔊 ทดสอบเสียงเหรียญแตก';b.onclick=()=>{soundUserMuted=false;enableSound();$('coinEnabled').checked=true;window.glassBreakSound();if(BrowserCamera.active)window.spawnCoachCoins($('arm').value,'rejected')};$('coinEnabled').parentElement.append(b)})();

(()=>{const line=document.createElement('p');line.className='purple-balance';line.dataset.i18nIgnore='';$('reps').parentElement.after(line);setInterval(()=>{const s=window.fitnessState;line.hidden=!s?.challenge;if(s?.challenge){const n=Math.min(20,20-s.challenge.remaining+s.reps);line.textContent=(window.I18N?.lang==='en'?'🎯 Challenge ':'🎯 ชาเลนจ์ ')+n+'/20 · 🟣 +1'}},400)})();
