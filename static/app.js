'use strict';
const $ = id => document.getElementById(id);
const labels = {left:'ซ้าย', right:'ขวา'};
const cueMap = {arm:'ลองให้ศอกใกล้ลำตัวอีกนิดนะ',torso:'ลองยืนตรง คุมลำตัวให้นิ่งนะ',tracking:'จัดกล้องให้เห็นไหล่ ศอก ข้อมือครบ',setup:'ปล่อยแขนลง ค้างนิ่ง 2 วินาทีนะ',flexion:'ลองงอศอกเพิ่มเท่าที่สบาย ไม่ต้องฝืนนะ',extension:'ค่อย ๆ ลดแขนลงเท่าที่สบาย',tempo:'ลองผ่อนจังหวะ คุมแรงขึ้นและลงนะ'};
let busy=false, polling=false, wasRunning=false, online=false, initialized=false, lastState=null;
let statusFailures=0,controlEpoch=0;
const controlRequests=new Set();
async function controlFetch(url,options={}){
 const c=new AbortController();controlRequests.add(c);let timer;
 try{return await Promise.race([fetch(url,{...options,signal:c.signal}),new Promise((_,reject)=>{timer=setTimeout(()=>{c.abort();reject(Error(accountText('รอนานเกินไป กดรีเซ็ตกล้องแล้วลองใหม่','Request timed out. Reset the camera and retry.')))},20000)})])}
 finally{clearTimeout(timer);controlRequests.delete(c)}
}
function cancelControls(){controlEpoch++;for(const c of controlRequests)c.abort();controlRequests.clear();busy=false}

let cameraError='';
let soundUserMuted=true;
let lastOutcomeId=0;
let soundEnabled=false, audioContext=null, lastSet=null, lastReps=null, lastPaused=false;
let speaking=false, voiceSerial=0, lastVoiceAt=0, spokenAt={}, lastSummary=null,lastGrowthSaved=null;
const voicePlayer=new Audio();
const audioUrls=new Map();
function setText(id,text){$(id).textContent=text}
function remember(key,value){try{localStorage.setItem(key,String(value))}catch(e){}}
function recalled(key){try{return localStorage.getItem(key)}catch(e){return null}}
async function cameraServerReset(rebuild=false){
 const epoch=controlEpoch;const valid=()=>{if(epoch!==controlEpoch)throw Error('Camera operation cancelled')};
 await window.ensureFitnessSession();valid();
 const r=await controlFetch('/status',{cache:'no-store'}),state=await r.json();
 valid();if(!r.ok)throw Error(state.error||'Cannot read camera state');
 const reset=await controlFetch('/camera/recover',{method:'POST',headers:{'X-Set-ID':state.set_id,'Content-Type':'application/json'},body:JSON.stringify({rebuild})}),body=await reset.json();
 valid();if(!reset.ok)throw Error(body.error||'Camera reset failed');
 BrowserCamera.adopt(body.state);lastState=body.state;wasRunning=false;return body.state;
}
async function post(path,data={}){
 const epoch=controlEpoch;const check=()=>{if(epoch!==controlEpoch)throw Error('Camera operation cancelled')};
 const opening=path==='/start'||path==='/plans/today/start'||path==='/cardio/start';let serverStarted=false;
 if(opening)data={...data,pose_quality:path==='/cardio/start'?'lite':($('poseQuality')?.value||'full'),person_count:path==='/start'?Number($('personCount')?.value||1):1,curl_target:Number($('curlTarget').value),grip_enabled:$('gripEnabled').checked,...(path!=='/cardio/start'?{difficulty:$('trainingDifficulty')?.value||'beginner',auto_arm:path==='/start'&&!!$('autoArm')?.checked}:{})};
 if(['/pause','/resume','/reset','/calibrate','/stop'].includes(path)){window.coachRevision++;window.latestFrameState=null;}
 if(path==='/stop'){BrowserCamera.close();cancelVoice()}
 try{
  if(opening){
   cameraError='';window.cameraFailure='';window.coachRevision++;window.latestFrameState=null;
   document.querySelectorAll('#exerciseTutorial video').forEach(v=>v.pause());
   if(!soundUserMuted&&($('teachEnabled').checked||$('coinEnabled').checked)){enableSound();unlockCoachAudio()}
   BrowserCamera.close();await cameraServerReset();check();
  }
  const r=await controlFetch(path,{method:'POST',headers:{'Content-Type':'application/json',...((path==='/stop'||opening)&&lastState?.set_id?{'X-Set-ID':lastState.set_id}:{})},body:JSON.stringify(data)});
  const b=await r.json();check();if(!r.ok)throw Error(b.error||'คำสั่งไม่สำเร็จ');
  if(!opening&&b.state){window.coachRevision++;BrowserCamera.adopt(b.state)}
  if(opening){
   serverStarted=true;let fresh=b.state;
   if(!fresh){const statusResponse=await controlFetch('/status',{cache:'no-store'});if(!statusResponse.ok)throw Error('Cannot start camera session');fresh=await statusResponse.json()}
   if(!fresh.running)throw Error('Workout did not start');
   window.coachRevision++;BrowserCamera.adopt(fresh);lastState=fresh;
   setText('status',accountText('กำลังเปิดกล้อง…','Opening camera…'));
   await BrowserCamera.open();check();
   // A long permission dialog can outlive the server's idle watchdog.
   const statusCheck=await controlFetch('/status',{cache:'no-store'});const current=await statusCheck.json();if(epoch!==controlEpoch)throw Error('Camera operation cancelled');
   if(!statusCheck.ok)throw Error(current.error||'Camera session expired');
   if(!current.running){
    const retry=await controlFetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Set-ID':current.set_id},body:JSON.stringify(data)});
    const result=await retry.json();check();if(!retry.ok)throw Error(window.I18N.t(result.error)||'Could not resume camera session');fresh=result.state;
   }else fresh=current;
   if(!fresh?.running)throw Error('Camera session did not start');
   lastState=fresh;
   BrowserCamera.adopt(fresh);lastSet=fresh.set_id;lastOutcomeId=0;lastReps=fresh.reps;lastPaused=fresh.paused;
   $('exercise').value=fresh.exercise;BrowserCamera.start();lastVoiceAt=Date.now();
   if(path!=='/cardio/start'&&$('teachEnabled').checked&&soundEnabled&&$('voiceEnabled').checked){try{speak(currentExercise().teaching||currentExercise().steps.join(' '),'teach_'+currentExercise().id,true)}catch(e){console.warn('Teaching audio unavailable',e)}}
  }
  return b;
 }catch(e){
  if(epoch!==controlEpoch)throw e;
  if(opening)window.cameraFailure=e.message;
  if(opening){BrowserCamera.close();if(serverStarted){try{await controlFetch('/stop',{method:'POST',headers:lastState?.set_id?{'X-Set-ID':lastState.set_id}:{}})}catch(stopError){console.warn('Camera stop unavailable',stopError)}}}
  console.error('[45 Fitness camera/control]',path,e);throw e;
 }
}
async function resetCamera(){
 cancelControls();
 await action(async()=>{
  window.coachRevision++;BrowserCamera.close();cancelVoice();cameraError='';window.cameraFailure='';
  await cameraServerReset(true);hideFeed();
  setText('captureInfo',accountText('รีเซ็ตกล้องแล้ว กดเปิดกล้องเพื่อเริ่มใหม่','Camera reset. Press Start to reopen.'));
 });
}
const catalogById=Object.fromEntries(exerciseCatalog.map(e=>[e.id,e]));
let renderedExercise='';
function currentExercise(){return catalogById[$('exercise').value]||catalogById.curl}
function sideText(ex,mode){if(ex.id==='split_squat')return mode==='left'?'ขาหน้าซ้าย':'ขาหน้าขวา';if(ex.group==='legs')return mode==='left'?'กล้องเห็นด้านซ้าย':'กล้องเห็นด้านขวา';return mode==='both'?'ทั้งสองข้าง':'แขน'+labels[mode]}
function selection(){
 const ex=currentExercise();$('future').hidden=true;$('curlPanel').hidden=false;
 if(renderedExercise!==ex.id){renderedExercise=ex.id;renderExerciseImages(ex);setText('exerciseName',ex.name);setText('exerciseGroup',ex.group_name+' · '+ex.tracking);setText('exerciseCamera','มุมกล้อง: '+ex.camera);setText('exerciseEquipment','อุปกรณ์: '+ex.equipment);setText('exerciseSetup',ex.setup);setText('exerciseLimit',ex.limitation);$('exerciseSource').href=ex.source;$('exerciseSteps').replaceChildren(...ex.steps.map(text=>{const li=document.createElement('li');li.textContent=text;return li}));$('curlGuide').hidden=true;setText('sideLabel',ex.id==='split_squat'?'ขาที่อยู่ด้านหน้า':ex.group==='legs'?'ด้านที่กล้องเห็น':'แขนที่เล่น');for(const o of $('arm').options){o.hidden=o.disabled=!ex.modes.includes(o.value);o.textContent=sideText(ex,o.value)}if(!ex.modes.includes($('arm').value))$('arm').value=ex.default_arm;setText('countRule',ex.group==='legs'?'กลับมาท่าเริ่มต้นครบหนึ่งรอบ = 1 ครั้ง · เลือกติดตามเข่าหรือสะโพกด้านเดียว':'กลับมาท่าเริ่มต้นครบหนึ่งรอบ = 1 ครั้ง · สองแขนต้องทำครบข้างละหนึ่งครั้ง = 1 รอบ');setText('metricLabel',ex.family==='squat'?'มุมเข่าโดยประมาณ':ex.family==='hinge'?'มุมสะโพกโดยประมาณ':ex.family==='raise'?'มุมต้นแขนกับลำตัว':'มุมศอกโดยประมาณ');setText('assessmentNote',ex.limitation);if(!wasRunning)setText('placeholder',ex.camera+' · '+ex.setup)}
 if(ex.family!=='curl')$('focus').value=ex.focus;else if($('focus').value==='full')$('focus').value='upper';
 $('focus').value=ex.focus;$('focus').disabled=true;$('curlTargetBox').hidden=ex.family!=='curl';$('curlTarget').disabled=wasRunning||busy;$('gripEnabled').disabled=wasRunning||busy;$('start').disabled=wasRunning||busy||!online||!$('profile').value||(window.VIPPage&&!window.VIPPage.can(ex.id));renderThresholds(Number($('tolerance').value));
}
function renderThresholds(t){
 const ex=currentExercise();let rows;const level=$('trainingDifficulty')?.value||'beginner',advanced=level!=='beginner',expert=level==='expert';if(advanced)t=({curl:[3,0],raise:[3,0]}[ex.family]||[4,1])[expert?1:0];const cfg=advanced?{...config,extension_count_grace_deg:expert?0:5,minimum_rep_excursion_deg:expert?65:55}:config,target=advanced?(expert?50:60):Number($('curlTarget').value);
 if(ex.family==='curl')rows=[['ช่วงลดที่ยอมให้นับ',`≥ ${Math.max(cfg.extension_target_deg-t-cfg.extension_count_grace_deg,Math.min(105,target+t)+25)}°`],['ช่วงงอที่ยอมให้นับ',`≤ ${Math.min(105,target+t)}°`],['ระยะเคลื่อนไหวขั้นต่ำ',`${Math.max(30,cfg.minimum_rep_excursion_deg-Math.max(0,t-10)*.35)}° ต่อรอบ`]];
 else{const specs={row:[150,80,45,false],triceps:[95,155,40,true],chest_press:[100,155,40,true],incline_press:[100,155,40,true],shoulder_press:[100,155,40,true],raise:[20,80,40,true],squat:[160,105,40,false],hinge:[165,105,40,false]};const [start,end,range,increasing]=specs[ex.family];const allowance=Math.min(t,(Math.abs(end-start)-20)/2),excursion=Math.max(25,range-Math.max(0,t-10)*.35);rows=[['ช่วงเริ่ม/กลับ',`${increasing?'≤':'≥'} ${start+(increasing?allowance:-allowance)}°`],['ช่วงปลายการเคลื่อนไหว',`${increasing?'≥':'≤'} ${end+(increasing?-allowance:allowance)}°`],['ระยะเคลื่อนไหวขั้นต่ำ',excursion+'° ต่อรอบ']]}
 rows.push(['ตั้งท่าเริ่มต้น','ค้างนิ่ง 2 วินาที'],['คำเตือนฟอร์ม','เกินเกณฑ์ต่อเนื่อง 0.9 วินาที'],['พักอัตโนมัติ','หยุดเคลื่อนไหว 8 วินาทีหลังนับได้ หรือครบเป้าหมายเซตในตาราง']);
 $('thresholds').replaceChildren(...rows.map(([a,b])=>{const tr=document.createElement('tr');for(const text of [a,b]){const td=document.createElement('td');td.textContent=text;tr.append(td)}return tr}));
}
function hideFeed(){$('feed').hidden=true;$('feed').removeAttribute('src');$('placeholder').hidden=false;$('overlay').hidden=true}
function shortCue(s){if(s.person_count>1)return (s.players||[]).map(p=>'P'+p.player_id+': '+p.reps).join(' · ')+(window.I18N?.lang==='en'?' · no saving':' · ไม่บันทึก');if(s.paused)return s.summary&&s.summary.plan_note?s.summary.plan_note:'พักก่อนนะ ♡ พร้อมแล้วเริ่มเซตถัดไป';const f=s.feedback[0],ex=catalogById[s.exercise]||currentExercise();return f?(f.arm?labels[f.arm]+' · ':'')+(ex.family==='curl'?(cueMap[f.code]||f.text):f.text):s.calibrated?'ทำต่อได้เลย ตามจังหวะที่สบาย ♡':ex.setup}
function coinDing(){if(!audioContext||!soundEnabled||!$('coinEnabled').checked)return;try{const now=audioContext.currentTime;[987.77,1318.51].forEach((frequency,i)=>{const o=audioContext.createOscillator(),g=audioContext.createGain(),at=now+i*.09;o.type='sine';o.frequency.setValueAtTime(frequency,at);g.gain.setValueAtTime(.001,at);g.gain.exponentialRampToValueAtTime(.13,at+.012);g.gain.exponentialRampToValueAtTime(.001,at+.2);o.connect(g);g.connect(audioContext.destination);o.start(at);o.stop(at+.21)})}catch(e){}}
function celebrate(){if(window.spawnCoachCoins)window.spawnCoachCoins(window.fitnessState?.arm||$('arm').value);$('reps').parentElement.classList.remove('celebrate');void $('reps').offsetWidth;$('reps').parentElement.classList.add('celebrate');coinDing()}
function cancelVoice(){voiceSerial++;voicePlayer.onended=null;voicePlayer.onerror=null;voicePlayer.pause();voicePlayer.removeAttribute('src');voicePlayer.load();if(window.speechSynthesis)window.speechSynthesis.cancel();speaking=false}
const voiceNoteObserver=new MutationObserver(()=>{const n=$('voiceSettingsNote');if(n)n.textContent=$('voiceNote').textContent});voiceNoteObserver.observe($('voiceNote'),{childList:true,characterData:true,subtree:true});
function canSpeak(serial){return serial===voiceSerial&&soundEnabled&&$('voiceEnabled').checked&&!document.hidden}

function voiceSpeed(){const speed=Number($('voiceSpeed').value);return Number.isFinite(speed)?Math.min(1.4,Math.max(.7,speed)):1}
function applyVoiceSpeed(){const speed=voiceSpeed();$('voiceSpeed').value=String(speed);setText('speedValue',speed.toFixed(2)+'×');voicePlayer.playbackRate=speed;voicePlayer.preservesPitch=true;remember('45-voice-speed',speed)}
function refreshVoices(){const selected=$('voiceChoice').value||recalled('45-voice-choice')||'auto',voices=window.speechSynthesis?window.speechSynthesis.getVoices():[];const options=[['auto','ไทย Neural ผู้หญิง (ค่าเริ่มต้น)'],['neural_female','ไทย Neural · เสียงผู้หญิง'],['neural_male','ไทย Neural · เสียงผู้ชาย'],['online','ไทยออนไลน์ · แบบเดิม'],['openai',voiceConfig.openai_available?'OpenAI · นุ่มนวล':'OpenAI · ต้องตั้ง API key'],...voices.filter(v=>v.lang.toLowerCase().startsWith(window.I18N?.lang==='en'?'en':'th')).map(v=>['device:'+v.voiceURI,v.name+' (อุปกรณ์)'])];if(!options.some(o=>o[0]===selected))options.push([selected,accountText('เสียงที่เลือกยังไม่พร้อม · กรุณาเลือกใหม่','Selected voice unavailable · choose another voice')]);$('voiceChoice').replaceChildren(...options.map(([value,text])=>{const o=document.createElement('option');o.value=value;o.textContent=text;o.disabled=value==='openai'&&!voiceConfig.openai_available;return o}));$('voiceChoice').value=selected;setText('openaiVoiceNote',voiceConfig.openai_available?'OpenAI พร้อมใช้งาน · การสร้างประโยคเสียงใหม่มีค่าบริการ API แยก':'OpenAI ต้องตั้ง API key บนคอมที่รัน Python ก่อน · เสียงไทย Neural ใช้ได้โดยไม่ตั้ง key')}
function playDeviceVoice(text,voice,serial){const synth=window.speechSynthesis;if(!canSpeak(serial)||!synth||!voice||!window.SpeechSynthesisUtterance)return false;voicePlayer.pause();synth.cancel();const u=new SpeechSynthesisUtterance(text);u.lang=window.I18N?.lang==='en'?'en-US':'th-TH';u.voice=voice;u.rate=.98*voiceSpeed();u.onend=()=>{if(serial===voiceSerial)speaking=false};u.onerror=()=>{if(serial===voiceSerial){speaking=false;setText('voiceNote','เสียงที่เลือกไม่พร้อม กรุณาเลือกเสียงอื่นเอง')}};synth.speak(u);setText('voiceNote','ใช้เฉพาะเสียงอุปกรณ์ที่เลือก · '+voice.name);return true}

function cueStillRelevant(code,force){if(force||!lastState)return true;if(code.startsWith('strict_')||['arm','torso','flexion','extension','tempo','tracking','setup','frame','position','steady','upper_still','soft_elbow','raise_height','knee_bend','grip_curl','grip_hammer','wrist','shoulders','range_option'].includes(code))return lastState.running&&!lastState.paused&&lastState.feedback.some(f=>f.code===code);if(code==='rest')return lastState.paused;return true}
async function speechUrl(code,provider){if(window.I18N?.lang==='en')code='en__'+code;const key=provider+':'+code;if(!audioUrls.has(key)){const r=await fetch('/speech/'+code+'.mp3?voice='+encodeURIComponent(provider));if(!r.ok){let message='เสียงออนไลน์ยังไม่พร้อม';try{message=(await r.json()).error||message}catch(e){}throw Error(message)}audioUrls.set(key,URL.createObjectURL(await r.blob()))}return audioUrls.get(key)}
async function speak(text,code='ready',force=false){
 if(window.fitnessState?.person_count>1)return;
 if(window.I18N){await window.I18N.ready;text=window.I18N.t(text)}
 if(document.hidden||!soundEnabled||!$('voiceEnabled').checked||speaking&&!force)return;
 cancelVoice();const serial=voiceSerial,choice=$('voiceChoice').value;const synth=window.speechSynthesis;
 speaking=true;
 if(choice.startsWith('device:')){const voices=synth?synth.getVoices():[],voice=voices.find(v=>v.voiceURI===choice.slice(7));if(!playDeviceVoice(text,voice,serial)){speaking=false;setText('voiceNote','ไม่พบเสียงที่เลือก กรุณาเลือกเสียงใหม่')}return}
 const provider=choice==='auto'?'neural_female':choice;
 try{
  setText('voiceNote','กำลังเตรียมเสียงที่เลือก…');const url=await speechUrl(code,provider);
  if(!canSpeak(serial))return;if(!cueStillRelevant(code,force)){speaking=false;return}
  if(synth)synth.cancel();voicePlayer.src=url;voicePlayer.playbackRate=voiceSpeed();voicePlayer.preservesPitch=true;
  voicePlayer.onended=()=>{if(serial===voiceSerial)speaking=false};
  voicePlayer.onerror=()=>{if(serial===voiceSerial){speaking=false;setText('voiceNote','เล่นเสียงที่เลือกไม่ได้ กดลองฟังอีกครั้ง')}};
  await voicePlayer.play();if(!canSpeak(serial))return;
  setText('voiceNote',provider==='openai'?'ใช้เฉพาะเสียง OpenAI ที่เลือก':provider==='neural_male'?'ใช้เฉพาะเสียงไทย Neural ผู้ชาย':provider==='neural_female'?'ใช้เฉพาะเสียงไทย Neural ผู้หญิง':'ใช้เฉพาะเสียงไทยออนไลน์');
 }catch(e){if(serial===voiceSerial){speaking=false;setText('voiceNote','เสียงที่เลือกยังไม่พร้อม · '+e.message+' · กดลองใหม่หรือเลือกเสียงอื่น')}}
}

function soundFeedback(s){if(s.person_count>1){cancelVoice();return}if(s.cardio)return;const same=lastSet===s.set_id;const previousPaused=lastPaused;if(!same)lastOutcomeId=0;if(Array.isArray(s.rep_events)){for(const event of s.rep_events){if(event.id<=lastOutcomeId)continue;lastOutcomeId=event.id;if(window.spawnCoachCoins)window.spawnCoachCoins(event.arm,event.result,event.result==='accepted'&&s.arm==='both'?'✓':null,event.difficulty||s.difficulty);if(event.result==='accepted')coinDing();else if(event.result==='rejected'&&window.glassBreakSound)window.glassBreakSound()} }else if(same&&lastReps!==null&&s.reps>lastReps)celebrate();if(!same){spokenAt={};lastVoiceAt=0;cancelVoice()}const now=Date.now();if(soundEnabled&&s.running&&!s.paused&&!speaking){const f=s.feedback[0];if(f){const key=f.code+':'+(f.arm||'');if(now-(spokenAt[key]||0)>16000&&now-lastVoiceAt>4000){spokenAt[key]=now;lastVoiceAt=now;speak(shortCue(s),f.code)}}else if(s.calibrated&&same&&lastState&&!lastState.calibrated&&now-lastVoiceAt>4000){lastVoiceAt=now;speak('พร้อมแล้ว ค่อย ๆ ทำตามจังหวะที่สบายนะ','ready')}}if(soundEnabled&&s.paused&&same&&!previousPaused){cancelVoice();speak('พักเซตแล้ว เก่งมาก ดูคำแนะนำสำหรับเซตถัดไปได้เลยนะ','rest')}lastSet=s.set_id;lastReps=s.reps;lastPaused=s.paused}
function renderFeedback(s){const level=s.paused?'ok':s.form_level||'unknown';$('formBox').className='panel feedback '+level;$('bigCue').parentElement.className='distance-panel '+level;setText('bigCue',shortCue(s));setText('formTitle',s.paused?'พักก่อน แล้วเริ่มใหม่เมื่อพร้อมนะ':s.form_title);const items=s.paused?[{text:'ดูคำแนะนำในช่องพักเซตได้เลย'}]:s.feedback.length?s.feedback:[{text:s.calibrated?'ค่อย ๆ ทำตามจังหวะที่สบาย และควบคุมช่วงกลับ':'ค้างท่าเริ่มต้นนิ่ง ๆ แล้วระบบจะเริ่มนับ'}];$('feedbackList').replaceChildren(...items.map(f=>{const li=document.createElement('li');li.textContent=f.text;return li}));$('overlay').className='overlay '+level;setText('overlay',shortCue(s));$('checks').replaceChildren(...(s.checks.length?s.checks:[{label:'แขนที่เลือก',status:'unknown'}]).map(c=>{const row=document.createElement('div');row.className='check '+c.status;const label=document.createElement('span');label.textContent=c.label;const badge=document.createElement('span');badge.className='badge';badge.textContent=c.display|| (c.status==='unknown'?'ไม่ประเมิน':`${c.value}° · ${c.status==='warn'?'ลองปรับ':c.status==='pending'?'กำลังดู':'ในเกณฑ์'}`);row.append(label,badge);return row}));$('progress').style.width=(s.calibration||0)+'%';soundFeedback(s)}
function renderRest(s){const summary=s.summary;$('restPanel').hidden=!summary;if(!summary)return;setText('restTitle',summary.title||accountText('พักคาร์ดิโอแล้ว','Cardio stopped'));setText('savedNote',summary.save_error||`${summary.profile_name||''} · ${summary.saved?'บันทึกอันดับแล้ว ✓':'เริ่มนับได้ในเซตถัดไป'} · ${summary.flagged||0} ครั้งมีคำแนะนำ`);$('restTips').replaceChildren(...(Array.isArray(summary.tips)?summary.tips:[]).map(text=>{const li=document.createElement('li');li.textContent=text;return li}));if(summary.plan_note)setText('savedNote',$('savedNote').textContent+' · '+summary.plan_note);if(summary.saved&&!summary.save_error&&lastGrowthSaved!==summary.set_id){lastGrowthSaved=summary.set_id;window.dispatchEvent(new Event('fitness-workout-saved'))}if(summary.saved&&lastSummary!==summary.set_id){lastSummary=summary.set_id;loadRanks();if(window.Planner)window.Planner.refresh()}}
async function poll(){if(polling||busy||BrowserCamera.opening)return;polling=true;const revision=window.coachRevision;try{let s;if(window.latestFrameState&&Date.now()-window.latestFrameState.at<900&&!busy){s=window.latestFrameState.state}else{const r=await fetch('/status',{cache:'no-store'});if(!r.ok)throw Error('status error');s=await r.json()}if(revision!==window.coachRevision)return;if(!BrowserCamera.observe(s))return;statusFailures=0;online=true;if(!initialized){$('tolerance').value=String(s.user_tolerance??s.thresholds.tolerance);initialized=true}if(s.running){cameraError='';$('exercise').value=s.exercise;$('arm').value=s.arm;$('focus').value=s.focus;$('camera').value=String(s.camera);$('tolerance').value=String(s.user_tolerance??s.thresholds.tolerance);if(s.profile){if(!Array.from($('profile').options).some(o=>o.value===String(s.profile.id)))await loadProfiles(s.profile.id);$('profile').value=String(s.profile.id)}}setText('repLabel',s.arm==='both'?'รอบครบสองข้างเซตนี้':'จำนวนครั้งเซตนี้ · '+(s.arm==='auto'?accountText('สลับแขนอัตโนมัติ','Automatic arms'):labels[s.arm]));setText('reps',s.reps);setText('flagged',s.flagged);setText('lastRep',s.last_rep);setText('angle',s.arm==='both'?'ซ้าย / ขวา':s.angle===null?'—':s.angle+'°');for(const a of ['left','right']){const o=s.arms[a];setText(a+'Reps',o?o.reps:'—');setText(a+'Angle',o&&o.angle!==null?o.angle+'°':'—')}setText('phase',s.paused?'กำลังพักเซต':s.phase);if(!busy)setText('status',window.cameraFailure||(cameraError&&!s.running?cameraError:s.message));renderFeedback(s);renderRest(s);window.PersonTracking?.update(s);for(const id of ['exercise','arm','focus','camera','tolerance','profile','profileName','addProfile'])$(id).disabled=s.running||busy;$('stop').disabled=!s.running||busy;$('calibrate').disabled=!s.running||s.paused||busy;$('pause').disabled=!s.running||s.paused||busy;$('resume').hidden=!s.running||!s.paused||!!s.plan;$('resume').disabled=busy;$('reset').disabled=busy||!!s.plan;if(s.running&&!wasRunning){setText('placeholder','กำลังรับภาพจากกล้องของคุณ…')}if(!s.running&&wasRunning){hideFeed();cancelVoice()}wasRunning=s.running;lastState=s;BrowserCamera.observe(s);selection();if(window.Planner)window.Planner.onStatus(s)}
 catch(e){if(revision!==window.coachRevision||busy||BrowserCamera.opening)return;statusFailures++;if(BrowserCamera.active){setText('status',window.I18N?.lang==='en'?'Connection interrupted; retrying…':'การเชื่อมต่อสะดุด กำลังลองใหม่…');return}online=false;setText('status','เชื่อมต่อไม่ได้ — ตรวจว่า PowerShell ยังรัน app.py');for(const id of ['start','stop','pause','resume','calibrate','reset'])$(id).disabled=true;setText('bigCue','รอเชื่อมต่อกับคอม');setText('formTitle','ยังประเมินไม่ได้');$('formBox').className='panel feedback unknown';$('feedbackList').replaceChildren();$('checks').replaceChildren();$('progress').style.width='0%';hideFeed();wasRunning=false;cancelVoice();if(window.Planner)window.Planner.onOffline()}finally{polling=false}}
async function action(fn){if(busy)return;const epoch=controlEpoch;busy=true;for(const id of ['start','stop','reset','pause','resume','calibrate','exercise','arm','focus','camera','tolerance','profile','profileName','addProfile'])$(id).disabled=true;let error=null;try{await fn()}catch(e){error=e.message}finally{if(epoch!==controlEpoch)return;busy=false;if(error)cameraError=error;await poll();if(error)setText('status',error)}}
async function loadProfiles(selectId=null){try{const r=await fetch('/profiles',{cache:'no-store'});if(!r.ok)throw Error();const data=await r.json();const previous=selectId||$('profile').value||recalled('45-profile')||window.defaultFitnessProfile;const blank=document.createElement('option');blank.value='';blank.textContent='เลือกชื่อก่อนเริ่ม';$('profile').replaceChildren(blank,...data.profiles.map(p=>{const option=document.createElement('option');option.value=String(p.id);option.textContent=p.name;return option}));if(previous&&data.profiles.some(p=>String(p.id)===String(previous)))$('profile').value=String(previous);else if(data.profiles.length)$('profile').value=String(data.profiles[0].id);if($('profile').value)remember('45-profile',$('profile').value);populateHealthProfiles(data.profiles);if(window.Planner)window.Planner.onProfiles(data.profiles);selection()}catch(e){setText('profileNote','ยังโหลดชื่อผู้เล่นไม่ได้ ลองรีเฟรชเมื่อคอมเชื่อมต่อแล้ว')}}
async function loadRanks(){loadStreakRanks();try{const r=await fetch('/leaderboard?exercise='+encodeURIComponent($('rankExercise').value)+'&arm='+encodeURIComponent($('rankArm').value),{cache:'no-store'});if(!r.ok)throw Error();const data=await r.json();$('rankRows').replaceChildren(...data.rows.map(row=>{const tr=document.createElement('tr');if(String(row.profile_id)===$('profile').value)tr.className='rank-me';for(const value of [row.rank===1?'✦ 1':row.rank,row.name,row.total,row.best_set,row.sets]){const td=document.createElement('td');td.textContent=String(value);if(tr.children.length===1){td.className='rank-name';window.PlayerName(td,row);if(row.rank===1){const crown=document.createElement('img');crown.src='/static/images/crown.svg';crown.alt='มงกุฎอันดับหนึ่ง';crown.className='crown-icon';td.append(crown)}}tr.append(td)}return tr}));$('rankEmpty').hidden=!!data.rows.length;setText('rankEmpty',$('rankExercise').value==='exercise2'?'ท่า 2 ยังไม่เปิดเล่น':'ยังไม่มีเซตที่บันทึก มาเริ่มเซตแรกกัน ♡')}catch(e){$('rankRows').replaceChildren();$('rankEmpty').hidden=false;setText('rankEmpty','โหลดอันดับไม่ได้ ตรวจว่าโปรแกรมบนคอมยังทำงานอยู่')}}
function setTab(page,options={}){
 page=page===true?'leader':page===false?'workout':page;
 const names=['home','workout','leader','health','calendar','profile','rewards','challenges','vip','friends','admin','cardio','character','inbox','boxing'];
 if(!names.includes(page))return;
 if(page!=='boxing')window.Boxing?.leave();
 if(page!=='cardio')window.CardioPage?.leave();
 if(page!=='character')window.CharacterPage?.leave();
 if(page!=='profile')window.ProfileDashboard?.leave();
 for(const name of names){const panel=$(name+'Page'),tab=$(name+'Tab');if(panel)panel.hidden=name!==page;if(tab){tab.classList.add('tab');tab.classList.toggle('active',name===page);tab.setAttribute('aria-pressed',String(name===page))}}
 if(page!=='workout'){document.body.classList.remove('far-view');setText('distance','โหมดอ่านไกล')}
 const open={boxing:()=>window.Boxing?.open(),inbox:()=>window.Inbox?.open(),cardio:()=>window.CardioPage?.open(),friends:()=>window.Community?.openFriends(),admin:()=>window.Community?.openAdmin(),vip:()=>window.VIPPage?.open(),challenges:()=>window.ChallengesPage?.open(),rewards:()=>window.RewardsPage?.open(),profile:()=>window.ProfileDashboard?.open(),character:()=>window.CharacterPage?.open(options.id??null,!!options.member),calendar:()=>window.Planner?.open(),leader:()=>loadRanks(),health:()=>loadHealthHistory(healthLoadedProfile!==$('healthProfile').value)};
 document.dispatchEvent(new CustomEvent('fitness:navigate',{detail:page}));
 return open[page]?.();
}
$('workoutTab').onclick=()=>setTab('workout');$('leaderTab').onclick=()=>setTab('leader');$('healthTab').onclick=()=>setTab('health');$('calendarTab').onclick=()=>setTab('calendar');
$('rankExercise').onchange=loadRanks;$('rankArm').onchange=loadRanks;$('refreshRank').onclick=loadRanks;
$('addProfile').onclick=()=>action(async()=>{const result=await post('/profiles',{name:$('profileName').value});$('profileName').value='';remember('45-profile',result.profile.id);await loadProfiles(result.profile.id)});
$('profileName').onkeydown=e=>{if(e.key==='Enter'&&!$('addProfile').disabled)$('addProfile').click()};
$('profile').onchange=()=>{remember('45-profile',$('profile').value);selection();if(window.Planner)window.Planner.profileChanged();if($('profile').value){$('healthProfile').value=$('profile').value;remember('45-health-profile',$('profile').value);loadHealthHistory(true)}};
$('resetCamera').onclick=resetCamera;
$('start').onclick=()=>action(()=>post('/start',{exercise:$('exercise').value,arm:$('arm').value,focus:$('focus').value,camera:Number($('camera').value),tolerance:Number($('tolerance').value),profile_id:Number($('profile').value)}));
$('stop').onclick=()=>action(()=>post('/stop'));$('pause').onclick=()=>action(()=>post('/pause'));$('resume').onclick=()=>action(()=>post('/resume'));$('reset').onclick=()=>action(()=>post('/reset'));$('calibrate').onclick=()=>action(()=>post('/calibrate'));
$('exercise').onchange=()=>{renderedExercise='';selection()};$('tolerance').onchange=selection;
$('distance').onclick=()=>{const active=document.body.classList.toggle('far-view');setText('distance',active?'กลับหน้าปกติ':'โหมดอ่านไกล')};
const soundChannel=typeof BroadcastChannel!=='undefined'?new BroadcastChannel('45-coach-sound'):null;
if(soundChannel)soundChannel.onmessage=()=>{soundEnabled=false;soundUserMuted=true;if($('coachAudioEnabled'))$('coachAudioEnabled').checked=false;cancelVoice();$('sound').setAttribute('aria-pressed','false');setText('sound','เปิดเสียง');setText('voiceNote','เปิดเสียงในอีกแท็บแล้ว')};
function enableSound(){soundUserMuted=false;if($('coachAudioEnabled'))$('coachAudioEnabled').checked=true;if(soundChannel)soundChannel.postMessage('active');soundEnabled=true;$('sound').setAttribute('aria-pressed','true');setText('sound','ปิดเสียง');const Context=window.AudioContext||window.webkitAudioContext;if(Context&&!audioContext)audioContext=new Context();if(audioContext)audioContext.resume().catch(()=>{});refreshVoices()}
function disableSound(){soundUserMuted=true;soundEnabled=false;if($('coachAudioEnabled'))$('coachAudioEnabled').checked=false;cancelVoice();$('sound').setAttribute('aria-pressed','false');setText('sound','เปิดเสียง');setText('voiceNote','ปิดเสียงแล้ว')}
$('sound').onclick=()=>{if(soundEnabled){disableSound()}else{soundUserMuted=false;enableSound();unlockCoachAudio();coinDing();speak('เปิดเสียงแล้ว พร้อมช่วยดูฟอร์มนะ','enabled',true)}};
$('testVoice').onclick=()=>{enableSound();unlockCoachAudio();$('voiceEnabled').checked=true;speak('เปิดเสียงแล้ว พร้อมช่วยดูฟอร์มนะ','enabled',true)};
if($('coachAudioEnabled'))$('coachAudioEnabled').onchange=()=>{if($('coachAudioEnabled').checked){enableSound();unlockCoachAudio();setText('voiceNote','เปิดเสียงแล้ว · กดลองฟังเพื่อตรวจเสียงที่เลือก')}else{disableSound()}};
$('voiceEnabled').onchange=()=>{if(!$('voiceEnabled').checked)cancelVoice()};
$('voiceChoice').onchange=()=>{remember('45-voice-choice',$('voiceChoice').value);cancelVoice();if(soundEnabled)speak('เปิดเสียงแล้ว พร้อมช่วยดูฟอร์มนะ','enabled',true)};
$('voiceEnabled').onchange=()=>{if(!$('voiceEnabled').checked)cancelVoice()};
$('voiceSpeed').value=recalled('45-voice-speed')||'1';$('voiceSpeed').oninput=()=>{cancelVoice();applyVoiceSpeed()};applyVoiceSpeed();$('voiceChoice').value=recalled('45-voice-choice')||'auto';if(window.speechSynthesis)window.speechSynthesis.addEventListener('voiceschanged',refreshVoices);refreshVoices();
$('feed').onerror=()=>{if(wasRunning)setText('status','กำลังรอภาพถัดไปจากกล้องของคุณ')};
document.querySelectorAll('.reference-image').forEach(img=>{img.onerror=()=>{img.onerror=null;img.src=img.dataset.fallback}});
async function connection(){try{const r=await fetch('/connection');if(!r.ok)throw Error();const data=await r.json();renderShare(data);const container=$('phoneLinks');container.replaceChildren();if(!data.links.length){container.textContent='ยังไม่พบ IP เครือข่าย — เชื่อมคอมกับ Wi-Fi แล้วเปิดโปรแกรมใหม่';return}data.links.forEach((link,i)=>{const box=document.createElement('div');box.className='phone-link';const label=document.createElement('div');label.textContent='ลิงก์มือถือ · '+link.ip;const image=document.createElement('img');image.src='/connection-qr/'+i;image.alt='QR เปิด 45 Fitness Coach บนมือถือ';const a=document.createElement('a');a.href=link.url;a.textContent=link.url;a.target='_blank';a.rel='noopener';box.append(label,image,a);container.append(box)})}catch(e){setText('phoneLinks','รอเชื่อมต่อกับคอม')}}
window.addEventListener('pagehide',()=>{cancelVoice();for(const url of audioUrls.values())URL.revokeObjectURL(url);audioUrls.clear()});
selection();loadProfiles();poll();connection();setInterval(poll,400);setInterval(()=>{if(!$('leaderPage').hidden)loadRanks()},10000);

function setTheme(theme){theme=theme==='power'?'power':'spicy';document.body.dataset.theme=theme;remember('45-theme',theme);for(const option of ['power','spicy']){$(option+'Theme').classList.toggle('active',option===theme);$(option+'Theme').setAttribute('aria-pressed',String(option===theme))}setText('heroChip',theme==='power'?'แข็งแกร่งขึ้น ทีละเซต ⚡':'เล็ก ๆ แต่สม่ำเสมอ ♡')}
$('powerTheme').onclick=()=>setTheme('power');$('spicyTheme').onclick=()=>setTheme('spicy');setTheme(recalled('45-theme')||'spicy');
let healthBusy=false,healthLoadSerial=0,healthLoadedProfile=null;
const healthInputs=['healthDate','healthAge','healthHeight','healthWeight','healthFat','healthMuscle','healthGoal'];
function localToday(){const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
$('healthDate').value=localToday();$('healthDate').max=localToday();
function populateHealthProfiles(profiles){const current=$('healthProfile').value||recalled('45-health-profile')||$('profile').value;const blank=document.createElement('option');blank.value='';blank.textContent='เลือกชื่อผู้เล่น';$('healthProfile').replaceChildren(blank,...profiles.map(p=>{const option=document.createElement('option');option.value=String(p.id);option.textContent=p.name;return option}));if(profiles.some(p=>String(p.id)===String(current)))$('healthProfile').value=String(current);setHealthAvailability()}
function setHealthAvailability(){const enabled=!!$('healthProfile').value&&!healthBusy;for(const id of [...healthInputs,'analyzeHealth','saveHealth','newHealth'])$(id).disabled=!enabled;$('healthProfile').disabled=healthBusy;$('refreshHealth').disabled=!enabled;if(!$('healthProfile').value)setText('healthStatus','เลือกชื่อผู้เล่นที่โปรไฟล์ของฉันก่อนนะ')}
function healthData(){return{measured_on:$('healthDate').value,age:$('healthAge').value,height_cm:$('healthHeight').value,weight_kg:$('healthWeight').value,body_fat_pct:$('healthFat').value||null,muscle_kg:$('healthMuscle').value||null,goal:$('healthGoal').value}}
function fillHealth(data){for(const [id,key] of Object.entries({healthDate:'measured_on',healthAge:'age',healthHeight:'height_cm',healthWeight:'weight_kg',healthFat:'body_fat_pct',healthMuscle:'muscle_kg',healthGoal:'goal'}))$(id).value=data[key]===null?'':String(data[key])}
function renderHealth(analysis){$('healthResult').hidden=false;setText('healthBMI',analysis.bmi.toFixed(2));setText('healthCategory',analysis.category);setText('healthResultNote',analysis.note);setText('healthBodyWeight',analysis.inputs.weight_kg+' กก.');setText('healthFatMass',analysis.fat_mass_kg===null?'ยังไม่มีค่าที่วัด':analysis.fat_mass_kg+' กก.');setText('healthLeanMass',analysis.lean_mass_kg===null?'ยังไม่มีค่าที่วัด':analysis.lean_mass_kg+' กก.');setText('healthMuscleMass',analysis.muscle_kg===null?'ยังไม่ได้วัด':analysis.muscle_kg+' กก.');$('healthTips').replaceChildren(...analysis.tips.map(text=>{const li=document.createElement('li');li.textContent=text;return li}))}
function renderHealthRows(records){$('healthRows').replaceChildren(...records.map(record=>{const a=record.analysis,tr=document.createElement('tr');for(const value of [a.inputs.measured_on,a.inputs.weight_kg.toFixed(1),a.bmi.toFixed(2),a.inputs.body_fat_pct===null?'—':a.inputs.body_fat_pct,a.muscle_kg===null?'—':a.muscle_kg]){const td=document.createElement('td');td.textContent=String(value);tr.append(td)}const td=document.createElement('td'),button=document.createElement('button');button.type='button';button.className='secondary history-view';button.textContent='ดู';button.onclick=()=>{fillHealth(a.inputs);renderHealth(a);setText('healthStatus','กำลังดูข้อมูลวันที่ '+a.inputs.measured_on)};td.append(button);tr.append(td);return tr}));$('healthEmpty').hidden=!!records.length}
async function loadHealthHistory(fill=false){const profile=$('healthProfile').value,serial=++healthLoadSerial;if(fill)$('healthResult').hidden=true;$('healthRows').replaceChildren();$('healthEmpty').hidden=false;if(!profile){setText('healthOwner','ยังไม่ได้เลือกชื่อ');setHealthAvailability();return}try{const option=Array.from($('healthProfile').options).find(o=>o.value===profile);setText('healthOwner',option?option.textContent:'กำลังโหลด');setText('healthStatus','กำลังโหลดข้อมูลของผู้เล่น…');const r=await fetch('/profiles/'+encodeURIComponent(profile)+'/health',{cache:'no-store'});const data=await r.json();if(!r.ok)throw Error(window.I18N.t(data.error)||'โหลดข้อมูลไม่ได้');if(serial!==healthLoadSerial||$('healthProfile').value!==profile)return;setText('healthOwner',data.profile.name);healthLoadedProfile=profile;renderHealthRows(data.records);if(fill&&data.records.length){fillHealth(data.records[0].analysis.inputs);renderHealth(data.records[0].analysis)}else if(fill){for(const id of healthInputs)$(id).value=id==='healthDate'?localToday():id==='healthGoal'?'fitness':''}setText('healthStatus',data.records.length?'โหลดประวัติของ '+data.profile.name+' แล้ว':'ยังไม่มีประวัติ กรอกข้อมูลแล้วกดวิเคราะห์หรือบันทึกได้เลย');setText('healthEmpty','ยังไม่มีข้อมูลที่บันทึก')}catch(e){if(serial===healthLoadSerial){setText('healthStatus',e.message);setText('healthEmpty','โหลดประวัติไม่ได้')}}finally{if(serial===healthLoadSerial)setHealthAvailability()}}
async function analyzeOrSaveHealth(save){if(healthBusy||!$('healthProfile').value)return;if(!$('healthForm').reportValidity())return;const profile=$('healthProfile').value,data=healthData();healthBusy=true;healthLoadSerial++;setHealthAvailability();try{const result=await post(save?'/profiles/'+encodeURIComponent(profile)+'/health':'/health/analyze',data);const analysis=save?result.record.analysis:result.analysis;if(save){await loadHealthHistory(false);if($('healthProfile').value===profile)setText('healthStatus',result.record.new_record?'บันทึกข้อมูลของผู้เล่นคนนี้แล้ว ✓':'ข้อมูลวันที่นี้และค่าเดิมบันทึกไว้แล้ว ✓')}else setText('healthStatus','วิเคราะห์แล้ว ยังไม่ได้บันทึก');if($('healthProfile').value===profile)renderHealth(analysis)}catch(e){setText('healthStatus',e.message);$('healthResult').hidden=true}finally{healthBusy=false;setHealthAvailability()}}
$('healthProfile').onchange=()=>{remember('45-health-profile',$('healthProfile').value);loadHealthHistory(true)};
$('healthForm').onsubmit=e=>{e.preventDefault();analyzeOrSaveHealth(false)};$('saveHealth').onclick=()=>analyzeOrSaveHealth(true);$('refreshHealth').onclick=()=>loadHealthHistory(true);
$('newHealth').onclick=()=>{$('healthDate').value=localToday();$('healthResult').hidden=true;setText('healthStatus','ปรับค่าที่วัดวันนี้แล้วกดวิเคราะห์หรือบันทึกได้เลย');$('healthWeight').focus()};setHealthAvailability();

function renderShare(data){const url=data.share_url;$('shareReady').hidden=!url;if(url){$('shareUrl').value=url;$('openShare').href=url;const qr='/share/qr?url='+encodeURIComponent(url.split('?')[0]);if($('shareQr').getAttribute('src')!==qr)$('shareQr').src=qr;setText('shareStatus','เปิดแชร์แล้ว · ใช้มือถือคนละ Wi-Fi ก็เปิดได้')}else{setText('shareStatus','ยังไม่ได้เปิดแชร์ · รัน Start-Share.ps1 ใน PowerShell หน้าต่างที่สอง');$('shareUrl').value='';$('shareQr').removeAttribute('src')} }
async function copyShareLink(){const url=$('shareUrl').value;if(!url)return;try{if(!navigator.clipboard)throw Error();await navigator.clipboard.writeText(url);setText('shareStatus','คัดลอกลิงก์แล้ว ส่งให้คนที่จะเข้ามาเล่นได้เลย')}catch(e){$('shareUrl').focus();$('shareUrl').select();setText('shareStatus','เลือกลิงก์ให้แล้ว กด Ctrl+C หรือกดค้างแล้วคัดลอกบนมือถือ')}}
$('copyShare').onclick=copyShareLink;$('nativeShare').onclick=async()=>{if(!$('shareUrl').value)return;try{if(navigator.share)await navigator.share({title:'45 Fitness Coach',url:$('shareUrl').value});else await copyShareLink()}catch(e){if(e.name!=='AbortError')await copyShareLink()}};$('refreshShare').onclick=connection;setInterval(connection,10000);

function renderExerciseImages(ex){
 renderTutorial(ex);
 $('exerciseImages').replaceChildren(...(ex.images||[]).map((url,i)=>{const f=document.createElement('figure'),img=document.createElement('img'),caption=document.createElement('figcaption');img.src=url;img.alt=ex.name+' '+(i+1);img.loading='lazy';caption.textContent=ex.image_credit?(window.I18N?.lang==='en'?'Step ':'ภาพที่ ')+(i+1):(i?'ช่วงยก / ช่วงปลาย':'ท่าเริ่มต้น');img.onerror=()=>{img.hidden=true;caption.textContent='ดูภาพจากลิงก์แหล่งอ้างอิงด้านล่าง'};f.append(img,caption);return f}));$('imageSource').hidden=!!ex.image_credit;$('imageSource').href=ex.image_source||ex.source;$('guideTitle').textContent=ex.image_credit?(window.I18N?.lang==='en'?'Exercise demonstration by Trainer Jeff':'วิธีเล่นสอนโดยเทรนเนอร์ Jeff'):(window.I18N?.lang==='en'?'Exercise guide':'ภาพวิธีเล่นท่านี้');let note=$('jeffImageNote');if(!note){note=document.createElement('p');note.id='jeffImageNote';$('exerciseImages').after(note)}note.textContent=ex.image_note?(window.I18N?.lang==='en'?'The supplied demonstration is on the floor. A bench press requires a stable bench.':ex.image_note):'';
 if(window.I18N?.lang==='en')note.textContent=ex.image_note_en||'';
}
async function loadStreakRanks(){try{const r=await fetch('/leaderboard/streaks',{cache:'no-store'});if(!r.ok)return;const d=await r.json();$('streakRows').replaceChildren(...d.rows.map(row=>{const tr=document.createElement('tr');for(const value of [row.rank,row.name+(row.rank===1?' 👑':''),'🔥 '+row.current,row.best,row.completed]){const td=document.createElement('td');td.textContent=String(value);if(tr.children.length===1){td.setAttribute('data-i18n-ignore','');window.PlayerName(td,row);}tr.append(td)}return tr}));$('streakEmpty').hidden=d.rows.length>0}catch(e){}}
$('curlTarget').value=recalled('45-curl-target')||'80';$('curlTarget').oninput=()=>{setText('curlTargetValue',$('curlTarget').value+'°');remember('45-curl-target',$('curlTarget').value);selection()};$('curlTarget').oninput();

function unlockCoachAudio(){if(!soundEnabled)return;try{voicePlayer.src='data:audio/wav;base64,UklGRiYAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQIAAAAAAA==';const p=voicePlayer.play();if(p)p.catch(()=>{});}catch(e){}}

function renderTutorial(ex){
 const files={curl:'arm',floor_press:'chest',shoulder_press:'shoulder',goblet_squat:'leg'};
 let box=$('exerciseTutorial');if(!box){box=document.createElement('section');box.id='exerciseTutorial';$('exerciseImages').after(box)}
 for(const old of box.querySelectorAll('video')){old.pause();old.removeAttribute('src');old.load()}
 box.replaceChildren();box.hidden=!files[ex.id];if(!files[ex.id])return;
 const title=document.createElement('h3');title.textContent=accountText('คลิปสอน · ','Video tutorial · ')+ex.name;
 const clip=document.createElement('video');clip.controls=true;clip.playsInline=true;clip.preload='metadata';clip.src='/static/videos/'+files[ex.id]+'.mp4';clip.style.cssText='width:100%;max-height:540px;border-radius:16px;background:#111';
 box.append(title,clip);
}
