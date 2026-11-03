/* Lightweight, native winter UI. No image/video background or animation library. */
'use strict';
(() => {
 const hero=document.querySelector('.winter-hero');if(!hero)return;
 const en=window.I18N?.lang==='en',t=(th,eng)=>en?eng:th;
 const el=(tag,cls,text)=>{const n=document.createElement(tag);n.className=cls;if(text)n.textContent=text;return n};
 const svg=path=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${path}</svg>`;
 const icons={
  workout:'<path d="M6 8v8M3 10v4M18 8v8M21 10v4M6 12h12"/>',
  cardio:'<path d="m13 2-8 12h6l-1 8 9-12h-6l1-8Z"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 10h18m-13 5h2m4 0h2"/>',
  leader:'<path d="M8 3h8v7a4 4 0 0 1-8 0V3Zm0 2H4v3a4 4 0 0 0 4 4m8-7h4v3a4 4 0 0 1-4 4m-4 2v6m-4 1h8"/>',
  health:'<path d="M20.8 5a5.4 5.4 0 0 0-8.8 1 5.4 5.4 0 0 0-8.8-1C-1 10 6 16 12 21c6-5 13-11 8.8-16Z"/><path d="M5 11h4l2-3 2 6 2-3h4"/>',
  character:'<circle cx="12" cy="7" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
  rewards:'<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M5 12v9h14v-9M12 8v13m0-13c-9 0-7-8-3-5l3 5Zm0 0c9 0 7-8 3-5l-3 5Z"/>',
  chat:'<path d="M21 11a8 8 0 0 1-8 8H8l-5 3V7a4 4 0 0 1 4-4h6a8 8 0 0 1 8 8Z"/><path d="M7 8h9m-9 4h6"/>',
  admin:'<path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6l8-4Z"/><path d="m8 12 3 3 5-6"/>',
  boxing:'<path d="M7 15c-4-2-5-7-2-9l2 1V4c0-3 12-3 12 2v6c0 2-2 4-4 4H7Zm0 1v5h9v-5"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  focus:'<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/><circle cx="12" cy="12" r="3"/>'
 };
 const features=el('div','winter-features');for(const label of [t('เรียนรู้ท่า','Learn your form'),t('ฝึกผ่านกล้อง','Train with your camera'),t('ดูพัฒนาการ','Track progress')]){const item=el('span','',label);item.prepend(el('i',''));features.append(item)}hero.querySelector('.winter-copy').append(features);
 const wrap=el('div','winter-scene-wrap'),scene=el('div','winter-scene');scene.setAttribute('aria-label',t('เพื่อนหิมะในสตูดิโอฤดูหนาว','Snow friend in the winter studio'));
 const head=el('div','winter-scene-head');head.innerHTML='<span>SNOW STUDIO / 45</span><span class="winter-window-dots" aria-hidden="true"><i></i><i></i><i></i></span>';scene.append(head);
 for(const cls of ['winter-scene-grid','winter-orbit','winter-snowbank']){const n=el('div',cls);n.setAttribute('aria-hidden','true');scene.append(n)}
 for(const cls of ['one','two','three']){const n=el('span','winter-scene-flake '+cls,'❄');n.setAttribute('aria-hidden','true');scene.append(n)}
 const friend=el('button','winter-friend');friend.id='winterFriend';friend.type='button';friend.dataset.feedback='winter';friend.setAttribute('aria-label',t('ทักทายน้องหิมะ','Say hello to our snow friend'));
 friend.innerHTML=`<svg class="winter-mascot" viewBox="0 0 220 270" aria-hidden="true" focusable="false">
 <defs><radialGradient id="winterSnow" cx=".35" cy=".25" r=".8"><stop stop-color="#fff"/><stop offset=".65" stop-color="#e4f4fb"/><stop offset="1" stop-color="#9fcee3"/></radialGradient><linearGradient id="winterScarf" x2="1" y2="1"><stop stop-color="#87cddf"/><stop offset="1" stop-color="#4287ab"/></linearGradient></defs>
 <ellipse cx="109" cy="247" rx="66" ry="9" fill="#0e3b52" opacity=".13"/>
 <g stroke="#395b72" stroke-width="4" stroke-linecap="round" fill="none"><path d="m57 157-28-17m2 0-9-13m11 16-18 2"/><g class="snowman-arm"><path d="m166 152 28-29m-1 1 1-17m-1 17 15-4"/></g></g>
 <ellipse cx="110" cy="188" rx="66" ry="60" fill="url(#winterSnow)" stroke="#c5e8f8" stroke-width="1.5"/>
 <g class="snowman-scarf"><path d="M135 129q18 9 37 0l-3 45q-19 2-33-12Z" fill="url(#winterScarf)" stroke="#69afc6"/><path d="m143 154 25 7m-26 2 26 7" stroke="#b4e5ee" stroke-width="3"/></g>
 <circle cx="109" cy="94" r="47" fill="url(#winterSnow)" stroke="#c5e8f8" stroke-width="1.5"/>
 <path d="M64 71q-1-40 46-41q42 1 45 41" fill="#426e93" stroke="#8dbad3" stroke-width="2"/><path d="M74 57q35-8 72 0M81 44q27-7 53 0" stroke="#6f98b8" stroke-width="3" fill="none"/><rect x="60" y="64" width="99" height="17" rx="8.5" fill="#c6e9f7" stroke="#a4d1e4"/><circle cx="108" cy="23" r="13" fill="#eaf8ff"/>
 <g class="snowman-eyes" fill="#2e4b65"><circle cx="94" cy="98" r="3.8"/><circle cx="126" cy="98" r="3.8"/></g><ellipse cx="78" cy="112" rx="8" ry="4.5" fill="#e9b7c9" opacity=".7"/><ellipse cx="142" cy="112" rx="8" ry="4.5" fill="#e9b7c9" opacity=".7"/><path d="m109 106 19 4-19 5Z" fill="#eab078"/><path d="M101 122q10 8 19-1" stroke="#4d7188" stroke-width="2.8" stroke-linecap="round" fill="none"/>
 <path d="M68 131q42 17 84-1l3 19q-45 19-91 1Z" fill="url(#winterScarf)" stroke="#69afc6" stroke-width="1.5"/><path d="M67 143q42 17 85-2" fill="none" stroke="#afdfea" stroke-width="2"/>
 <g fill="#496f87"><circle cx="108" cy="176" r="4"/><circle cx="108" cy="195" r="4"/><circle cx="108" cy="214" r="4"/></g></svg>`;scene.append(friend);
 for(const [position,icon,title,sub] of [['top','clock','24 / 7',t('พร้อมทุกเวลา','Always here')],['bottom','focus',t('โฟกัสฟอร์ม','Focus on form'),t('ค่อย ๆ เก่งขึ้นด้วยกัน','One small step at a time')]]){const chip=el('div','winter-chip '+position);chip.innerHTML=svg(icons[icon]);const text=el('span','');text.append(el('strong','',title),el('small','',sub));chip.append(text);scene.append(chip)}
 const foot=el('div','winter-scene-footer');foot.innerHTML='<span><i class="winter-weather-dot"></i>WINTER CLUB</span><span>MOVE · BREATHE · REPEAT</span>';scene.append(foot);
 const controls=el('div','winter-scene-controls'),greeting=el('p','winter-greeting',t('แตะน้องหิมะ รับกำลังใจก่อนฝึก','Tap our snow friend for a little encouragement'));greeting.id='winterGreeting';greeting.setAttribute('role','status');greeting.setAttribute('aria-live','polite');
 const snowToggle=el('button','winter-snow-toggle');snowToggle.id='winterSnowToggle';snowToggle.type='button';controls.append(greeting,snowToggle);wrap.append(scene,controls);hero.append(wrap);
 document.querySelectorAll('.home-tile').forEach(card=>{const icon=card.querySelector('.home-tile-icon');if(icon)icon.innerHTML=svg(icons[card.dataset.feedback]||icons.focus);const arrow=el('span','activity-arrow');arrow.setAttribute('aria-hidden','true');card.append(arrow)});
 const weather=el('div','winter-weather');weather.setAttribute('aria-hidden','true');const air=el('div','winter-air'),canvas=el('canvas','winter-snow');weather.append(air,canvas);document.body.prepend(weather);const ctx=canvas.getContext('2d'),motion=matchMedia('(prefers-reduced-motion: reduce)');
 let snowOn=true;try{snowOn=localStorage.getItem('45fitness.winterSnow')!=='off'}catch{}
 let frame=0,last=0,time=0,frames=0,active=false,sceneVisible=true,width=0,height=0,flakes=[],windBias=0,color='#e8f8ff',wishTimer=0,count=0;
 function resize(){width=innerWidth;height=innerHeight;const dpr=Math.min(devicePixelRatio||1,1.5);canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);ctx?.setTransform(dpr,0,0,dpr,0,0);flakes=Array.from({length:width<600?42:88},(_,i)=>({x:Math.random()*width,y:Math.random()*height,r:.65+Math.random()*1.7,depth:.35+Math.random()*.65,phase:Math.random()*Math.PI*2,crystal:i%13===0}));}
 function draw(now){if(!active)return;const dt=Math.min(.045,Math.max(0,(now-(last||now))/1000));last=now;time+=dt;frames++;ctx.clearRect(0,0,width,height);const wind=24+Math.sin(time*.32)*19+Math.sin(time*.13)*13+windBias;
  ctx.fillStyle=color;ctx.strokeStyle=color;
  for(const f of flakes){f.x+=(wind*f.depth+Math.sin(time*.65+f.phase)*9)*dt;f.y+=(16+f.depth*29)*dt;if(f.y>height+12){f.y=-12;f.x=Math.random()*width}if(f.x>width+12)f.x=-12;if(f.x< -12)f.x=width+12;ctx.globalAlpha=.3+f.depth*.45;
   if(f.crystal){ctx.save();ctx.translate(f.x,f.y);ctx.rotate(time*.15+f.phase);ctx.lineWidth=.8;ctx.beginPath();for(let k=0;k<3;k++){const a=k*Math.PI/3,r=f.r*2.4;ctx.moveTo(Math.cos(a)*r,Math.sin(a)*r);ctx.lineTo(-Math.cos(a)*r,-Math.sin(a)*r)}ctx.stroke();ctx.restore()}else{ctx.beginPath();ctx.arc(f.x,f.y,f.r,0,Math.PI*2);ctx.fill()}
  }ctx.globalAlpha=1;frame=requestAnimationFrame(draw);
 }
 const clearWishes=()=>{clearTimeout(wishTimer);friend.classList.remove('is-waving');scene.querySelectorAll('.winter-wish').forEach(n=>n.remove())};
 function sync(){const home=document.body.dataset.homeActive==='true',allowed=document.body.dataset.effects==='on'&&!motion.matches;
  document.body.dataset.winterVisible=String(home&&sceneVisible&&!document.hidden);weather.hidden=!home||!allowed||!snowOn;
  snowToggle.disabled=!allowed;snowToggle.setAttribute('aria-pressed',String(snowOn&&allowed));snowToggle.textContent=!allowed?t('หิมะพักอยู่','Snow paused'):snowOn?t('พักหิมะ','Pause snow'):t('เปิดหิมะ','Let it snow');snowToggle.title=!allowed?t('พักตามการตั้งค่าเอฟเฟกต์ของคุณ','Paused by your motion preferences'):t('เปิดหรือพักหิมะพื้นหลัง','Toggle background snowfall');
  color=document.body.dataset.theme==='spicy'?'#739eb9':'#e8f8ff';const next=!!ctx&&home&&allowed&&snowOn&&!document.hidden;
  if(next&&!active){active=true;last=0;frame=requestAnimationFrame(draw)}else if(!next){active=false;cancelAnimationFrame(frame);last=0;ctx?.clearRect(0,0,width,height)}
  if(!home||!allowed||document.hidden)clearWishes();
 }
 snowToggle.addEventListener('click',()=>{snowOn=!snowOn;try{localStorage.setItem('45fitness.winterSnow',snowOn?'on':'off')}catch{}sync()});
 friend.addEventListener('click',()=>{clearWishes();count++;greeting.textContent=count%2?t('อุ่นเครื่องสักนิด แล้วไปเก่งขึ้นด้วยกันนะ','Warm up a little. Let’s grow stronger together.'):t('ทุกครั้งที่ขยับ คือก้าวเล็ก ๆ ที่น่าภูมิใจ','Every little move is a reason to feel proud.');if(document.body.dataset.effects!=='on'||motion.matches)return;friend.classList.add('is-waving');for(let i=0;i<5;i++){const wish=el('span','winter-wish','❄');wish.setAttribute('aria-hidden','true');wish.style.setProperty('--dx',((i-2)*32)+'px');wish.style.animationDelay=(i*.035)+'s';scene.append(wish)}wishTimer=setTimeout(clearWishes,1700)});
 new IntersectionObserver(([entry])=>{sceneVisible=entry.isIntersecting;sync()},{threshold:.05}).observe(scene);
 new MutationObserver(sync).observe(document.body,{attributes:true,attributeFilter:['data-home-active','data-effects','data-theme']});motion.addEventListener('change',sync);
 window.addEventListener('resize',resize,{passive:true});window.addEventListener('pointermove',e=>{if(active&&e.pointerType==='mouse')windBias=(e.clientX/width-.5)*15},{passive:true});
 document.addEventListener('visibilitychange',sync);document.addEventListener('fitness:navigate',()=>{clearWishes();sync()});window.addEventListener('pagehide',()=>{active=false;cancelAnimationFrame(frame);clearWishes()});window.addEventListener('pageshow',sync);
 resize();sync();window.WinterUI={get state(){return{active,frames,flakes:flakes.length,width,height,snowOn,sceneVisible}},destroy(){active=false;cancelAnimationFrame(frame);clearWishes();weather.remove()}};
})();
