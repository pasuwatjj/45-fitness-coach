/* Original sticker themes. Never replace a control, listener, ID, live value or photo. */
'use strict';
(() => {
 const byId={homeTab:'home',backHome:'home',workoutTab:'workout',calendarTab:'calendar',leaderTab:'leader',cardioTab:'cardio',healthTab:'health',characterTab:'character',profileTab:'profile',accountTab:'profile',vipTab:'vip',rewardsTab:'rewards',challengesTab:'challenges',friendsTab:'friends',adminTab:'admin',powerTheme:'workout',spicyTheme:'health'};
 const tileIcons=['workout','cardio','calendar','leader','health','character','rewards','admin'];
 const pageIcons={characterPage:'character',cardioPage:'cardio',friendsPage:'friends',adminPage:'admin',vipPage:'vip',challengesPage:'challenges',rewardsPage:'rewards',profilePage:'profile',calendarPage:'calendar',leaderPage:'leader',healthPage:'health'};
 // Strip only a leading presentation symbol, preserving all translated text, badges and counts.
 const leading=/^[\s\uFE0F\u200D\u2600-\u27BF\u2300-\u23FF\u25A0-\u25FF\u{1F300}-\u{1FAFF}]+/u;
 function mark(node,kind,iconOnly=false){
  if(!node)return;
  if(node.dataset.themeIcon!==kind)node.dataset.themeIcon=kind;
  node.classList.add('theme-sticker');
  if(iconOnly){node.classList.add('theme-sticker-only');node.setAttribute('aria-hidden','true');return}
  // Read and modify text nodes in place; controls retain identity and accessible names.
  const text=[...node.childNodes].find(n=>n.nodeType===3&&n.textContent.trim());
  if(text){const clean=text.textContent.replace(leading,'');if(clean&&clean!==text.textContent)text.textContent=clean}
 }
 function decorate(){
  for(const [id,kind] of Object.entries(byId))mark(document.getElementById(id),kind);
  document.querySelectorAll('.home-tile-icon').forEach((n,i)=>mark(n,tileIcons[i]||'star',true));
  document.querySelectorAll('.home-group').forEach(n=>mark(n.querySelector('summary'),n.dataset.group||'workout'));
  for(const [id,kind] of Object.entries(pageIcons)){
   const page=document.getElementById(id);if(page)mark(page.querySelector('h2'),kind);
  }
  document.querySelectorAll('.friend-chat h3').forEach(n=>mark(n,'chat'));
  document.querySelectorAll('#friendsPage button').forEach(n=>{if(/แชต|\bChat\b/.test(n.textContent))mark(n,'chat')});
  const hero=document.querySelector('.home-hero');
  if(hero&&!hero.querySelector('.theme-garden')){
   const art=document.createElement('div');art.className='theme-garden';art.setAttribute('aria-hidden','true');hero.append(art);
  }
 }
 // Only navigation labels and newly rendered page content are watched. No attribute watcher,
 // timers or frame loop; disconnect around our edits so decoration cannot trigger itself.
 let queued=false,passes=0;
 const watch=()=>observer.observe(document.body,{childList:true,subtree:true,characterData:true});
 const observer=new MutationObserver(records=>{
  if(queued||!records.some(r=>{
   const node=r.target.nodeType===1?r.target:r.target.parentElement;
   return node&&(node.closest('.account-bar,.home-hero,.home-tiles,.home-categories,.friend-chat')||
     (node.closest('#mainApp')&&[...r.addedNodes].some(n=>n.nodeType===1&&n.matches('h2,h3,button,section,.panel'))));
  }))return;
  queued=true;queueMicrotask(()=>{queued=false;observer.disconnect();decorate();passes++;watch()});
 });
 decorate();watch();
 window.FitnessThemes={refresh(){observer.disconnect();decorate();passes++;watch()},get passes(){return passes}};
})();
