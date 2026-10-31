'use strict';
// The four original artwork files are supplied by the site owner.
window.CoinArt=(()=>{
 const types={beginner:['yellow-muscle.png','🟡','เหรียญผู้เริ่มต้น','Beginner coin'],pro:['purple-muscle.png','🟣','เหรียญ Pro','Pro coin'],expert:['expert-muscle.png','🔴','เหรียญ Expert','Expert coin'],universal:['blue-universal.png','🌐','เหรียญสากล','Universal coin']};
 function create(currency='beginner'){
  const key=Object.hasOwn(types,currency)?currency:'beginner',data=types[key],node=document.createElement('span');
  node.className='coin-art '+key;node.dataset.currency=key;node.setAttribute('role','img');node.setAttribute('aria-label',data[window.I18N?.lang==='en'?3:2]);
  const fallback=document.createElement('span');fallback.className='coin-art-fallback';fallback.textContent=data[1];fallback.setAttribute('aria-hidden','true');
  const img=document.createElement('img');img.alt='';img.draggable=false;img.hidden=true;
  img.onload=()=>{img.hidden=false;fallback.remove();node.dataset.artwork='ready'};
  img.onerror=()=>{img.hidden=true;node.dataset.artwork='unavailable'};
  img.src='/static/images/coins/'+data[0];node.append(fallback,img);return node;
 }
 function text(node,value){
  const mapping={'🟡':'beginner','🟣':'pro','🔴':'expert','🌐':'universal','🪙':'beginner'};
  node.replaceChildren(...String(value).split(/(🟡|🟣|🔴|🌐|🪙)/u).filter(Boolean).map(part=>mapping[part]?create(mapping[part]):document.createTextNode(part)));return node;
 }
 return{create,text};
})();
