'use strict';
// Slot numbers are session labels, never recognized human identities.
window.PersonTracking=(()=>{
 const colors=['#7be9b2','#8bc8ff'];
 const text=(th,en)=>window.I18N?.lang==='en'?en:th;
 const make=(tag,label,cls)=>{const n=document.createElement(tag);if(label)n.textContent=label;if(cls)n.className=cls;return n};
 const box=make('section',null,'panel person-panel');box.dataset.i18nIgnore='';
 const label=make('label');label.htmlFor='personCount';const select=make('select');select.id='personCount';select.innerHTML='<option value="1">1</option><option value="2">2</option>';
 const note=make('p',null,'note'),status=make('p',null,'note'),choices=make('div',null,'person-choices'),cards=make('div',null,'person-cards');status.setAttribute('role','status');
 box.append(label,select,note,status,choices,cards);document.querySelector('.screen').before(box);
 let signature='',pending=false;
 function update(s){
  const multi=(s?.running?s.person_count:Number(select.value))>1;select.disabled=!!s?.running||!!(typeof BrowserCamera!=='undefined'&&BrowserCamera.opening)||pending;
  if(s?.running)select.value=String(s.person_count||1);
  label.textContent=text('จำนวนคน','Number of players');select.options[0].textContent=text('1 คน · บันทึกตามปกติ','1 player · normal saving');select.options[1].textContent=text('2 คน · เล่นชั่วคราว ไม่บันทึก','2 players · temporary, no saving');
  note.textContent=multi?text('โหมด 2 คนแยกนับและแนะนำบนหน้าจอ ไม่บันทึกสถิติ มุม เหรียญ EXP ตาราง สตรีก หรือชาเลนจ์ ปิดเสียงโค้ชและการดูมือ ยืนแยกกันให้เห็นไหล่และสะโพกครบ','Two independent counters and on-screen coaching. No stats, angles, coins, EXP, plans, streaks or challenges are saved. Voice and hand checks are off. Stand apart with both shoulders and hips visible.'):text('ติดตามคนเดิมจากตำแหน่งลำตัว เมื่อหลุดหรือซ้อนกันจะหยุดนับ ให้เลือกคนใหม่ด้านล่าง การเลือกจะล้างจำนวนและเริ่มวัดใหม่ ไม่ใช่การยืนยันตัวบุคคล','Follows torso position. Counting stops on loss or overlap; select a person below to restart. Selection clears that slot’s counts and measurements. This is not identity recognition.');
  const track=s?.tracking;const active=s?.running&&!s?.cardio;
  status.textContent=active?(track?.status||[]).map((v,i)=>'P'+(i+1)+' · '+({locked:text('กำลังติดตาม','Tracking'),waiting:text('รอคนยืนแยกกัน / เลือกคน','Stand apart / select'),lost:text('หลุด · เลือกใหม่','Lost · select again'),ambiguous:text('คนซ้อนกัน · แยกแล้วเลือกใหม่','Overlap · separate and select again')}[v]||v)).join(' | '):'';
  const sig=JSON.stringify([active,s?.paused,track?.candidates,track?.status,select.value,window.I18N?.lang]);
  if(sig!==signature&&!pending){signature=sig;choices.replaceChildren();if(active&&!s.paused){const candidates=[...(track?.candidates||[])].sort((a,b)=>Number(document.getElementById('camera').value)===1?a.x-b.x:b.x-a.x);for(let slot=0;slot<(s.person_count||1);slot++)for(const [j,c] of candidates.entries()){const b=make('button',text(`เลือกคน ${j+1} จากซ้าย → P${slot+1} (เริ่มใหม่)`,`Person ${j+1} from left → P${slot+1} (restart)`),'secondary');b.type='button';b.style.borderColor=colors[slot];b.onclick=async()=>{pending=true;choices.querySelectorAll('button').forEach(x=>x.disabled=true);try{window.coachRevision++;window.latestFrameState=null;const r=await controlFetch('/tracking/select',{method:'POST',headers:{'Content-Type':'application/json','X-Set-ID':s.set_id},body:JSON.stringify({slot,x:c.x,y:c.y})}),body=await r.json();if(!r.ok)throw Error(body.error);BrowserCamera.adopt(body.state);lastState=body.state;BrowserCamera.clearPoints();cancelVoice()}catch(e){status.textContent=e.message}finally{pending=false;signature=''}};choices.append(b)}}}
  cards.replaceChildren();if(active&&multi)for(const p of s.players||[]){const card=make('article',null,'person-card');card.style.borderColor=colors[p.player_id-1];card.append(make('strong','P'+p.player_id),make('div',String(p.reps??0)+' '+text('ครั้ง','reps'),'person-reps'));for(const [side,a] of Object.entries(p.arms||{}))card.append(make('p',`${side==='left'?text('ซ้าย','Left'):text('ขวา','Right')}: ${a.reps} · ${a.angle==null?'—':a.angle+'°'}`));const feedback=p.feedback?.[0];card.append(make('p',text('ไม่นับ / ไม่ชัด: ','Rejected / unclear: ')+(p.rejected||0)+' / '+(p.unverified||0)));card.append(make('p',feedback?(window.I18N?.t(feedback.text)||feedback.text):text('เริ่มจากท่าเริ่มต้น แล้วทำให้ครบช่วง','Begin from neutral, then complete the full movement')));cards.append(card)}
  document.getElementById('formBox').hidden=!!(active&&multi);
  document.getElementById('checks').hidden=!!(active&&multi);
  if(active&&multi){document.getElementById('status').textContent=s.paused?text('พักเซต 2 คน · ไม่บันทึกผล','2-player set paused · nothing saved'):text('โหมด 2 คน · แยกนับ ไม่บันทึกผล','2 players · independent counts, nothing saved');}
  const count=document.querySelector('.count-card');if(count)count.hidden=!!(active&&multi);
  if(active&&multi){document.getElementById('pause').textContent=text('พักเซต · ไม่บันทึก','Pause · no saving');document.getElementById('reset').textContent=text('เริ่มนับใหม่ · ไม่บันทึก','Reset counts · no saving');if(s.summary)document.getElementById('savedNote').textContent=text('โหมด 2 คน · ผลอยู่เฉพาะเซตนี้ ไม่มีการบันทึกหรือรางวัล','2-player mode · results stay in this session. Nothing saved; no rewards.')}else{document.getElementById('pause').textContent=text('พักเซต + บันทึก','Pause + save');document.getElementById('reset').textContent=text('บันทึก + เริ่มนับใหม่','Save + reset')}
 }
 // Immediate local overlay uses only unambiguous candidates near the server's
 // locked anchors. Missing/overlapping candidates clear immediately.
 function match(payload,state){const rows=payload.poses||[],track=state?.tracking;return (track?.anchors||[]).map((a,slot)=>{
  if(!a||track.status[slot]!=='locked')return {player_id:slot+1,landmarks:[]};
  const valid=rows.map(p=>{const torso=(a.mode==='left'?[11,23]:a.mode==='right'?[12,24]:[11,12,23,24]).map(i=>p[i]);if(torso.some(q=>!q||(q.visibility??0)<.5))return null;return{p,x:torso.reduce((v,q)=>v+q.x,0)/torso.length,y:torso.reduce((v,q)=>v+q.y,0)/torso.length}}).filter(Boolean);
  const ranked=valid.map(v=>({...v,d:Math.hypot(v.x-a.x,v.y-a.y)})).sort((x,y)=>x.d-y.d),v=ranked[0];
  if(!v||v.d>.42*Math.max(.1,a.scale)||(ranked[1]&&ranked[1].d-v.d<.35*Math.max(.1,a.scale))||valid.some(q=>q!==v&&q.p!==v.p&&Math.hypot(q.x-v.x,q.y-v.y)<Math.max(.16,a.scale*.85)))return{player_id:slot+1,landmarks:[]};
  return{player_id:slot+1,landmarks:v.p.map(p=>[p.x,p.y,p.visibility??0])};
 })}
 select.onchange=()=>update(window.fitnessState);setInterval(()=>update(window.fitnessState),350);update();return{update,match,colors};
})();
