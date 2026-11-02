/* Native, independently animated UI. Ghost outline/face retained from power-garden.svg. */
'use strict';
(() => {
 const hero=document.querySelector('.festival-hero');if(!hero)return;
 const en=window.I18N?.lang==='en',el=(tag,cls,text)=>{const n=document.createElement(tag);n.className=cls;if(text)n.textContent=text;return n};
 const scene=el('div','festival-scene');scene.dataset.sceneVisible='true';
 const sky=el('div','festival-sky');sky.setAttribute('aria-hidden','true');sky.innerHTML='<span class="festival-moon">☾</span><span class="festival-star star-one">✦</span><span class="festival-star star-two">✧</span><span class="festival-star star-three">✦</span>';scene.append(sky);
 const friend=el('button','festival-friend');friend.type='button';friend.id='festivalGhost';friend.dataset.feedback='festival';friend.setAttribute('aria-label',en?'Say hello to the Loy Krathong ghost':'ทักทายน้องผีลอยกระทง');
 friend.innerHTML=`<svg class="festival-mascot" viewBox="35 0 175 200" aria-hidden="true" focusable="false"><g stroke="#694977" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
 <g class="ghost-body"><path d="M56 101c0-85 126-85 126 0v65l-21-13-21 13-21-13-21 13-21-13-21 13Z" fill="#fff3dd"/>
 <g class="ghost-eyes"><circle cx="97" cy="105" r="4" fill="#694977"/><circle cx="138" cy="105" r="4" fill="#694977"/></g><path d="M109 119q9 10 18 0" fill="none"/><ellipse cx="80" cy="119" rx="10" ry="5" fill="#f8b59d" stroke="none"/><ellipse cx="154" cy="119" rx="10" ry="5" fill="#f8b59d" stroke="none"/>
 <path class="ghost-sabai" d="M61 128q62 20 117-47l5 20q-56 70-124 47Z" fill="#a7d9bf"/><path d="M61 140q67 21 119-46" fill="none" stroke="#edc578" stroke-width="4"/>
 <g class="ghost-flower" fill="#f6bdcf" stroke-width="2"><ellipse cx="160" cy="42" rx="7" ry="14" transform="rotate(-40 160 42)"/><ellipse cx="175" cy="42" rx="7" ry="14" transform="rotate(40 175 42)"/><ellipse cx="167" cy="36" rx="7" ry="14"/><circle cx="168" cy="48" r="5" fill="#f7d886"/></g>
 <g class="ghost-arm"><path d="M178 120q21-17 19-29q-1-7-7-2l-10 13" fill="#fff3dd"/></g></g></g></svg>`;
 scene.append(friend);
 const river=el('div','festival-river');river.setAttribute('aria-hidden','true');river.innerHTML='<i class="river-ring"></i><i class="river-ring ring-two"></i><i class="river-ring ring-three"></i>';
 const krathong=el('div','festival-krathong');krathong.setAttribute('aria-hidden','true');
 krathong.innerHTML='<svg viewBox="0 0 140 110" focusable="false"><g stroke="#694977" stroke-width="2.5" stroke-linejoin="round"><path d="M17 69q14-33 34-21l19-23 19 23q20-12 34 21l-14 27H31Z" fill="#96c4a6"/><path d="M32 71Q25 31 55 56Q70 18 85 56Q115 31 108 71Q70 100 32 71Z" fill="#efb5cb"/><path d="M35 83q35 13 70 0l-7 17H42Z" fill="#7da993"/><path d="M65 61V30h10v31" fill="#fff0b8"/><path class="candle-flame" d="M70 8q-17 20 0 24q17-4 0-24Z" fill="#ffce75" stroke="#d79c54"/></g></svg>';
 river.append(krathong);scene.append(river);
 const actions=hero.querySelector('.festival-actions');hero.append(scene,actions);
 const greeting=el('p','festival-greeting',en?'A little wave, a little brighter. Tap our ghost!':'แตะทักทายน้องผี เติมรอยยิ้มให้วันนี้');greeting.id='festivalGreeting';greeting.setAttribute('role','status');greeting.setAttribute('aria-live','polite');hero.append(greeting);
 let timer=0,count=0;const clear=()=>{clearTimeout(timer);friend.classList.remove('is-waving');scene.querySelectorAll('.festival-wish').forEach(n=>n.remove())};
 friend.addEventListener('click',()=>{clear();count++;greeting.textContent=en?(count%2?'A little joy, floated your way.':'One small move. One stronger you.'):(count%2?'ลอยความเหนื่อยไป เติมพลังให้ตัวเองนะ':'ขยับอีกนิด เก่งขึ้นอีกหน่อย ไปด้วยกันนะ');
  if(document.body.dataset.effects!=='on'||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  friend.classList.add('is-waving');const wish=el('span','festival-wish','✦');wish.setAttribute('aria-hidden','true');scene.append(wish);timer=setTimeout(clear,1700);
 });
 document.addEventListener('fitness:navigate',clear);document.addEventListener('visibilitychange',()=>{if(document.hidden)clear()});
 new IntersectionObserver(([entry])=>scene.dataset.sceneVisible=String(entry.isIntersecting),{threshold:.1}).observe(scene);
 // Give each existing category an interactive UI ornament, never replace its control.
 document.querySelectorAll('.home-tile').forEach(card=>{const arrow=el('span','activity-arrow');arrow.setAttribute('aria-hidden','true');card.append(arrow)});
})();
