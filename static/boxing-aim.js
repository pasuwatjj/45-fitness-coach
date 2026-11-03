'use strict';
// Native pointer challenge. Only the server can confirm hits, evasion and damage.
window.BoxingAimHUD=class{
 constructor(arena,t,send){
  this.arena=arena;this.t=t;this.send=send;this.pending=new Set();
  const make=(tag,cls,text='')=>{const n=document.createElement(tag);n.className=cls;n.textContent=text;return n};
  this.root=make('section','boxing-aim');this.root.hidden=true;this.root.setAttribute('aria-label',t('หลบฤาษีบดยา','Evade Ruesi Bod Ya'));
  const header=make('header','boxing-aim-header');this.title=make('strong','','TIME STOP');this.note=make('span');header.append(this.title,this.note);
  this.board=make('div','boxing-aim-board');this.timer=make('output','boxing-aim-timer');this.target=make('button','boxing-aim-target');this.target.type='button';this.target.setAttribute('aria-label',t('กดเป้าเพื่อหลบ','Hit target to evade'));this.target.hidden=true;
  this.board.append(this.timer,this.target);this.progress=make('p','boxing-aim-progress');this.help=make('p','boxing-aim-help');this.root.append(header,this.board,this.progress,this.help);arena.append(this.root);
  this.target.addEventListener('pointerdown',e=>{e.preventDefault();e.stopPropagation();this.hit(this.target.dataset.target)});
  this.target.addEventListener('click',e=>{e.stopPropagation();if(e.detail===0)this.hit(this.target.dataset.target)});
  this.board.addEventListener('pointerdown',()=>{if(this.defender&&this.now()<this.special.challenge.ends_at)this.hit(null)});
 }
 now(){return (Date.now()+this.offset)/1000}
 update(match,me,offset){
  const s=match?.status==='active'?match.special:null;this.offset=offset;
  if(!s?.challenge){this.reset();return}
  if(this.special?.id!==s.id){clearTimeout(this.noticeTimer);this.notice?.remove();this.pending.clear();this.arena.classList.remove('boxing-aim-evaded')}
  this.special=s;this.defender=s.target===me;
  if(s.phase==='evaded'){
   this.reset(true);this.special=s;this.arena.classList.add('boxing-aim-evaded');
   if(this.noticeId!==s.id){this.noticeId=s.id;clearTimeout(this.noticeTimer);this.notice=document.createElement('div');this.notice.className='boxing-aim-result';this.notice.setAttribute('role','status');this.notice.textContent=this.t('หลบสกิลสำเร็จ · ดาเมจ 0','EVADED · 0 DAMAGE');this.arena.append(this.notice);this.noticeTimer=setTimeout(()=>this.notice?.remove(),2300)}return;
  }
  const playing=s.phase==='aim';this.root.hidden=!playing;this.arena.classList.toggle('boxing-aim-active',playing);
  if(!playing){cancelAnimationFrame(this.frame);this.frame=null;return}
  this.title.textContent=this.defender?this.t('หยุดเวลา · กดเป้าเพื่อหลบ','TIME STOP · EVADE'):this.t('หยุดเวลา · ฝ่ายรับกำลังหลบ','TIME STOP · DEFENDER CHALLENGE');
  this.note.textContent=s.challenge.urgent?this.t('HP ต่ำกว่า 50% · เป้าจะเร็วขึ้น','HP BELOW 50% · ACCELERATING'):this.t('HP ตั้งแต่ 50% · จังหวะปานกลาง','HP 50% OR MORE · STEADY PACE');
  this.help.textContent=this.defender?this.t('กดทุกเป้าให้ทันจนครบ 10 วินาทีเพื่อหลบ · พลาดแล้วรับดาเมจ 50% ของ HP สูงสุด','Hit every target for 10 seconds to evade · A miss triggers damage of 50% MAX HP'):this.t('ทั้งคู่หยุดนิ่ง · หากฝ่ายรับพลาดจะเข้าสู่คัทซีน','Both fighters are frozen · A defender miss triggers the cinematic');
  if(!this.frame)this.tick();
 }
 hit(id){
  if(!this.defender||this.special?.phase!=='aim'||id&&this.pending.has(id))return;
  const specialId=this.special.id;if(id)this.pending.add(id);
  this.send('special_aim',{special_id:specialId,target_id:id}).catch(()=>{if(this.special?.id===specialId&&id)this.pending.delete(id)});
 }
 tick(){
  if(this.root.hidden){this.frame=null;return}
  const c=this.special.challenge,now=this.now(),remaining=Math.max(0,c.ends_at-now),current=c.targets.find(v=>now>=v.opens_at&&now<v.closes_at);
  this.timer.textContent=remaining>0?remaining.toFixed(1):this.t('ตรวจผล…','Checking…');
  const hits=c.targets.filter(v=>v.hit||this.pending.has(v.id)).length,misses=c.stray_misses+c.targets.filter(v=>now>v.closes_at+.18&&!v.hit&&!this.pending.has(v.id)).length;
  this.progress.textContent=`${this.t('เป้าที่กด','TARGETS')} ${hits} / ${c.targets.length}  ·  ${this.t('พลาด','MISSED')} ${misses}`;
  this.target.hidden=!current||!!current.hit||this.pending.has(current?.id);this.target.disabled=!this.defender;
  if(current){this.target.dataset.target=current.id;this.target.style.left=current.x*100+'%';this.target.style.top=current.y*100+'%';this.target.style.setProperty('--remaining',Math.max(0,(current.closes_at-now)/(current.closes_at-current.opens_at)))}
  this.frame=requestAnimationFrame(()=>this.tick());
 }
 reset(keepNotice=false){if(!keepNotice){clearTimeout(this.noticeTimer);this.notice?.remove();this.noticeId=null}cancelAnimationFrame(this.frame);this.frame=null;this.root.hidden=true;this.arena.classList.remove('boxing-aim-active','boxing-aim-evaded');this.special=null;this.pending.clear();}
};
