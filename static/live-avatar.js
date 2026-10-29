'use strict';
window.LiveAvatar=(()=>{
 const t=(th,en)=>window.I18N?.lang==='en'?en:th,screen=document.querySelector('.screen');
 const wrap=document.createElement('aside');wrap.className='live-avatar';wrap.hidden=true;wrap.dataset.i18nIgnore='';
 const canvas=document.createElement('canvas');canvas.width=300;canvas.height=360;canvas.setAttribute('aria-label',t('ตัวละครของฉันตามท่าที่ตรวจพบ','My character following detected movement'));
 const caption=document.createElement('small');wrap.append(canvas,caption);screen.append(wrap);
 const stabilizer=AvatarPose.createStabilizer();
 const toggles=[];let enabled=true,key='',requestKey='',modelSet='',generation=0,controller=null,model=null,renderer=null,frame=null,lastDraw=-Infinity,lastSample=null,lastRig=null;
 function toggle(parent,id){if(!parent)return;const label=document.createElement('label');label.className='live-avatar-toggle';label.dataset.i18nIgnore='';const input=document.createElement('input');input.type='checkbox';input.id=id;input.checked=true;label.append(input,document.createTextNode(t('แสดงตัวละครของฉัน','Show my character')));parent.append(label);toggles.push(input);input.onchange=()=>{enabled=input.checked;try{if(key)localStorage.setItem('45fitness.liveAvatar.'+key,enabled?'1':'0')}catch{}toggles.forEach(e=>e.checked=enabled);sync()};}
 toggle(document.querySelector('.camera-arm-tools'),'showLiveAvatar');toggle(document.getElementById('cardioPage'),'showCardioAvatar');
 function clear(){stabilizer.reset();generation++;controller?.abort();controller=null;model=null;renderer?.destroy();renderer=null;wrap.hidden=true;if(frame!==null)cancelAnimationFrame(frame);frame=null;lastRig=null;lastSample=null;}
 async function load(pid,token){const mine=generation;controller=new AbortController();try{const r=await fetch('/profiles/'+pid+'/character',{cache:'no-store',signal:controller.signal});const data=await r.json();if(mine!==generation||token!==fitnessToken||String(pid)!==String(window.fitnessState?.profile?.id||document.getElementById('profile').value))return;if(!r.ok||!data.created||String(data.profile?.id)!==String(pid))return;model=data;renderer=new FitnessCharacterRenderer(canvas);canvas.tabIndex=-1;renderer.set(model);renderer.stop();sync()}catch(e){if(e.name!=='AbortError'&&mine===generation)console.warn('[45 avatar] Could not load saved character',e.message)}finally{if(mine===generation)controller=null}}
 function current(){return window.fitnessState||{}}
 function loop(time){frame=null;if(wrap.hidden||document.hidden||!renderer)return;const s=current();if(!BrowserCamera.active||!s.running||s.person_count>1){sync();return}if(time-lastDraw>=1000/30){lastDraw=time;const rect=canvas.getBoundingClientRect(),ratio=Math.min(2,devicePixelRatio||1),w=Math.max(1,Math.round(rect.width*ratio)),h=Math.max(1,Math.round(rect.height*ratio));if(canvas.width!==w)canvas.width=w;if(canvas.height!==h)canvas.height=h;const sample=window.coachLandmarks;const rig=stabilizer.update(AvatarPose.solve(sample,s),s,Date.now());lastSample=sample;lastRig=rig;renderer.setLivePose(rig);caption.textContent=rig.held?t('กำลังจับตำแหน่งใหม่','Reacquiring'):rig.valid?t('ตามท่าที่ตรวจพบ','Following your pose'):t('รอการตรวจจับ','Waiting for tracking');wrap.classList.toggle('live-avatar-floor',rig.floor);wrap.classList.toggle('live-avatar-full',rig.full)}frame=requestAnimationFrame(loop)}
 function sync(){const s=current(),pid=String(s.profile?.id||document.getElementById('profile')?.value||''),token=typeof fitnessToken==='undefined'?'':fitnessToken,identity=token+':'+pid;
  if(identity!==requestKey){clear();loaded.clear();modelSet='';requestKey=identity;key=pid;try{enabled=localStorage.getItem('45fitness.liveAvatar.'+key)!=='0'}catch{enabled=true}toggles.forEach(e=>e.checked=enabled);}
  const active=BrowserCamera.active&&s.running&&s.person_count!==2&&!document.hidden&&!screen.closest('[hidden]');
  if(active&&modelSet!==s.set_id){clear();modelSet=s.set_id;}
  if(active&&enabled&&!model&&!controller&&pid&&token&&!loaded.has(requestKey+':'+s.set_id)){loaded.add(requestKey+':'+s.set_id);load(pid,token)}
  const shown=!!(active&&enabled&&model&&renderer);wrap.hidden=!shown;
  if(!shown){if(frame!==null)cancelAnimationFrame(frame);frame=null;lastRig=null;lastSample=null;return}
  if(frame===null)frame=requestAnimationFrame(loop);
 }
 const loaded=new Set();document.addEventListener('visibilitychange',sync);window.addEventListener('pagehide',clear);
 setInterval(sync,200);sync();return{sync,get visible(){return !wrap.hidden},get pose(){return lastRig},get profileId(){return model?.profile?.id||null}};
})();
