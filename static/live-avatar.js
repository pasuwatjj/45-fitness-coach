'use strict';
window.LiveAvatar=(()=>{
 const t=(th,en)=>window.I18N?.lang==='en'?en:th,screen=document.querySelector('.screen');
 const wrap=document.createElement('aside');wrap.className='live-avatar';wrap.hidden=true;wrap.dataset.i18nIgnore='';
 function newCanvas(){const c=document.createElement('canvas');c.width=300;c.height=360;c.setAttribute('aria-label',t('ตัวละครของฉันตามท่าที่ตรวจพบ','My character following detected movement'));return c}
 let canvas=newCanvas();
 const caption=document.createElement('small');wrap.append(canvas,caption);screen.append(wrap);
 const stabilizer=AvatarPose.createStabilizer();
 const sizeControls=[];let sizePercent=100;
 const toggles=[];let retryAt=0,enabled=true,key='',requestKey='',modelSet='',generation=0,controller=null,model=null,renderer=null,frame=null,lastDraw=-Infinity,lastSample=null,lastRig=null;
 function toggle(parent,id){if(!parent)return;const label=document.createElement('label');label.className='live-avatar-toggle';label.dataset.i18nIgnore='';const input=document.createElement('input');input.type='checkbox';input.id=id;input.checked=true;label.append(input,document.createTextNode(t('แสดงตัวละครของฉัน','Show my character')));const controls=document.createElement('div');controls.className='live-avatar-controls';controls.append(label);parent.append(controls);toggles.push(input);
 const sizeLabel=document.createElement('label');sizeLabel.className='live-avatar-size';sizeLabel.dataset.i18nIgnore='';
 const slider=document.createElement('input');slider.type='range';slider.min='60';slider.max='220';slider.step='10';slider.value=String(sizePercent);slider.id=id+'Size';
 const output=document.createElement('output');output.htmlFor=slider.id;sizeLabel.htmlFor=slider.id;
 sizeLabel.append(document.createTextNode(t('ขนาดตัวละคร','Avatar size')),slider,output);controls.append(sizeLabel);sizeControls.push({slider,output});
 slider.oninput=()=>{sizePercent=Number(slider.value);try{if(key)localStorage.setItem('45fitness.liveAvatarSize.'+key,String(sizePercent))}catch{}applySize()};
 input.onchange=()=>{enabled=input.checked;try{if(key)localStorage.setItem('45fitness.liveAvatar.'+key,enabled?'1':'0')}catch{}toggles.forEach(e=>e.checked=enabled);sync()};}
 toggle(document.querySelector('.camera-arm-tools'),'showLiveAvatar');toggle(document.getElementById('cardioPage'),'showCardioAvatar');
 function applySize(){
  sizeControls.forEach(({slider,output})=>{slider.value=String(sizePercent);output.value=sizePercent+'%';slider.setAttribute('aria-valuetext',sizePercent+'%')});
  const floor=wrap.classList.contains('live-avatar-floor'),mobile=matchMedia('(max-width:420px)').matches;
  const bw=floor?(mobile?110:190):(mobile?88:150),bh=floor?(mobile?84:135):(mobile?116:180);
  const rect=screen.getBoundingClientRect(),top=parseFloat(getComputedStyle(wrap).top)||8;
  const factor=Math.max(.1,Math.min(sizePercent/100,Math.max(40,rect.width*.46-12)/bw,Math.max(40,rect.height-top-12)/bh));
  wrap.style.width=Math.round(bw*factor)+'px';wrap.style.height=Math.round(bh*factor)+'px';
 }
 const sizeObserver=new ResizeObserver(applySize);sizeObserver.observe(screen);window.addEventListener('resize',applySize);
 function clear(){stabilizer.reset();generation++;controller?.abort();controller=null;model=null;renderer?.destroy();renderer=null;const fresh=newCanvas();canvas.replaceWith(fresh);canvas=fresh;retryAt=0;wrap.hidden=true;if(frame!==null)cancelAnimationFrame(frame);frame=null;lastRig=null;lastSample=null;}
 async function load(pid,token){const mine=generation;retryAt=Date.now()+5000;controller=new AbortController();try{const r=await fetch('/profiles/'+pid+'/character',{cache:'no-store',signal:controller.signal});const data=await r.json();if(mine!==generation||token!==fitnessToken||String(pid)!==String(window.fitnessState?.profile?.id||document.getElementById('profile').value))return;if(!r.ok)return;if(!data.created||String(data.profile?.id)!==String(pid)){retryAt=Infinity;return;}model=data;renderer=new FitnessImportedAvatar(canvas);canvas.tabIndex=-1;renderer.setDumbbells(true);renderer.set(model);renderer.stop();sync()}catch(e){if(e.name!=='AbortError'&&mine===generation)console.warn('[45 avatar] Could not load saved character',e.message)}finally{if(mine===generation)controller=null}}
 function current(){return window.fitnessState||{}}
 function loop(time){frame=null;if(wrap.hidden||document.hidden||!renderer)return;const s=current();if(!BrowserCamera.active||!s.running||s.person_count>1){sync();return}if(time-lastDraw>=1000/30){lastDraw=time;const sample=window.coachLandmarks;const rig=stabilizer.update(AvatarPose.solve(sample,s),s,Date.now());lastSample=sample;lastRig=rig;renderer.setLivePose(rig);caption.textContent=canvas.dataset.avatarState==='loading'?t('กำลังโหลดตัวละคร','Loading avatar'):canvas.dataset.avatarState==='error'?t('โหลดตัวละครไม่ได้','Avatar unavailable'):rig.held?t('กำลังจับตำแหน่งใหม่','Reacquiring'):rig.valid?t('ตามท่าที่ตรวจพบ','Following your pose'):t('รอการตรวจจับ','Waiting for tracking');if(wrap.classList.contains('live-avatar-floor')!==rig.floor){wrap.classList.toggle('live-avatar-floor',rig.floor);applySize()}wrap.classList.toggle('live-avatar-full',rig.full)}frame=requestAnimationFrame(loop)}
 function sync(){const s=current(),pid=String(s.profile?.id||document.getElementById('profile')?.value||''),token=typeof fitnessToken==='undefined'?'':fitnessToken,identity=token+':'+pid;
  if(identity!==requestKey){clear();modelSet='';requestKey=identity;key=pid;try{enabled=localStorage.getItem('45fitness.liveAvatar.'+key)!=='0'}catch{enabled=true}toggles.forEach(e=>e.checked=enabled);
   try{const saved=Number(localStorage.getItem('45fitness.liveAvatarSize.'+key));sizePercent=Number.isFinite(saved)&&saved>=60&&saved<=220?Math.round(saved/10)*10:100}catch{sizePercent=100}applySize();}
  if(!BrowserCamera.active&&(renderer||controller)){clear();modelSet='';}
  const active=BrowserCamera.active&&s.running&&!(s.person_count>1)&&!document.hidden&&!screen.closest('[hidden]');
  if(active&&modelSet!==s.set_id){clear();modelSet=s.set_id;}
  if(active&&enabled&&!model&&!controller&&pid&&token&&Date.now()>=retryAt){load(pid,token)}
  const shown=!!(active&&enabled&&model&&renderer);wrap.hidden=!shown;
  if(!shown){if(frame!==null)cancelAnimationFrame(frame);frame=null;lastRig=null;lastSample=null;return}
  if(frame===null){applySize();frame=requestAnimationFrame(loop)}
 }
 document.addEventListener('visibilitychange',sync);window.addEventListener('pagehide',clear);
 setInterval(sync,200);sync();return{sync,get visible(){return !wrap.hidden},get pose(){return lastRig},get profileId(){return model?.profile?.id||null}};
})();
