'use strict';
// Presentation only. Match timestamps and skill eligibility remain server-owned.
window.BoxingSkillHUD=class{
 constructor(arena,t){
  this.arena=arena;this.t=t;this.key=null;this.timer=null;
  this.hud=document.createElement('div');this.hud.className='boxing-time-hud';this.hud.hidden=true;
  this.active=document.createElement('strong');this.active.className='boxing-time-active';
  this.rows=document.createElement('div');this.rows.className='boxing-time-players';this.hud.append(this.active,this.rows);
  this.cue=document.createElement('div');this.cue.className='boxing-time-cue';this.cue.hidden=true;this.cue.setAttribute('role','status');
  this.cue.innerHTML='<div class="boxing-time-wave"></div><div class="boxing-time-dial" aria-hidden="true"><svg viewBox="0 0 200 200"><circle cx="100" cy="100" r="93"/><circle cx="100" cy="100" r="80"/><path d="M100 22v12m78 66h-12M100 178v-12M22 100h12M45 45l8 8m102-8-8 8m8 102-8-8M45 155l8-8"/><g class="boxing-time-hands"><path d="M100 45v55l35 20"/></g><circle cx="100" cy="100" r="5"/></svg></div><strong>TIME SHIFT</strong><span></span>';
  arena.append(this.hud,this.cue);
 }
 static time(ms){const s=Math.max(0,Math.ceil(ms/1000));return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')}
 stopCue(){clearTimeout(this.timer);this.timer=null;this.cue.hidden=true;this.arena.classList.remove('boxing-time-flash')}
 reset(){this.stopCue();this.hud.hidden=true;this.key=null}
 update(match,me,wall,keyName,specialKey='X'){
  const t=this.t,live=match?.status==='active',visible=!!match&&['active','countdown','round_break'].includes(match.status);
  this.hud.hidden=!visible;if(!visible){this.stopCue();return}
  const remaining=live?Math.max(0,(match.slow_until||0)*1000-wall):0;
  this.active.hidden=!remaining;this.active.textContent=t('สโลว์ทั้งคู่','BOTH SLOWED')+' · '+BoxingSkillHUD.time(remaining);
  const signature=match.players.map(p=>p.uid).join(',');
  if(this.rows.dataset.players!==signature){this.rows.replaceChildren();this.rows.dataset.players=signature;for(const p of match.players){const row=document.createElement('div');row.className='boxing-time-player';row.dataset.uid=p.uid;row.append(document.createElement('small'),document.createElement('b'),document.createElement('span'));this.rows.append(row)}}
  for(const [i,p] of match.players.entries()){
   const row=this.rows.children[i],cooldown=Math.max(0,(p.skill_ready_at||0)*1000-wall),own=p.uid===me;
   row.firstChild.textContent=(own?t('คุณ','YOU'):t('คู่ต่อสู้','OPPONENT'))+' · '+keyName;
   row.children[1].textContent=cooldown? t('คูลดาวน์ ','CD ')+BoxingSkillHUD.time(cooldown):remaining?t('รอสโลว์จบ','WAIT'):live?t('พร้อมใช้','READY'):t('รอยกเริ่ม','NEXT ROUND');
   const specialCD=Math.max(0,(p.special_ready_at||0)*1000-wall),busy=live&&wall<((match.special?.started_at||0)+(match.special?.duration||0))*1000;
   row.lastChild.textContent=specialKey+' · '+(specialCD?BoxingSkillHUD.time(specialCD):busy?t('รอ','WAIT'):live?t('พร้อม','READY'):t('รอยก','WAIT'));
   row.dataset.state=cooldown?'cooldown':remaining||!live?'waiting':'ready';
  }
  if(!remaining){this.stopCue();return}
  const key=match.id+':'+match.slow_until;
  if(key===this.key)return;this.key=key;
  const started=(match.slow_started_at??match.slow_until-60)*1000;
  if(wall-started>3000||document.hidden)return;
  this.stopCue();this.cue.querySelector('span').textContent=(match.slow_by===me?t('คุณใช้สกิล','YOU ACTIVATED'):t('คู่ต่อสู้ใช้สกิล','OPPONENT ACTIVATED'))+' · '+t('สโลว์ 1 นาที','60s SLOW');
  this.cue.hidden=false;this.arena.classList.add('boxing-time-flash');this.timer=setTimeout(()=>this.stopCue(),1600);
 }
};
