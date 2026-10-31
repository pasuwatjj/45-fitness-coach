'use strict';
// Generated for 45 Fitness Coach from the owner-approved color/emblem direction.
// A single transparent PNG atlas keeps all four currencies cached together.
window.CoinArt=(()=>{
 const types={beginner:['beginner','🟡','เหรียญผู้เริ่มต้น','Beginner coin'],pro:['pro','🟣','เหรียญ Pro','Pro coin'],expert:['expert','🔴','เหรียญ Expert','Expert coin'],universal:['universal','🌐','เหรียญสากล','Universal coin']};
 function create(currency='beginner'){
  const key=Object.hasOwn(types,currency)?currency:'beginner',data=types[key],node=document.createElement('span');
  node.className='coin-art '+key;node.dataset.currency=key;node.setAttribute('role','img');node.setAttribute('aria-label',data[window.I18N?.lang==='en'?3:2]);
  const fallback=document.createElement('span');fallback.className='coin-art-fallback';fallback.textContent=data[1];fallback.setAttribute('aria-hidden','true');
  const img=document.createElement('img');img.alt='';img.draggable=false;img.hidden=true;
  img.onload=()=>{img.hidden=false;fallback.remove();node.dataset.artwork='ready'};
  img.onerror=()=>{img.hidden=true;node.dataset.artwork='unavailable'};
  img.src='/static/images/coins/fitness-coins.png?v=1';node.append(fallback,img);return node;
 }
 function text(node,value){
  if(node.dataset.coinText===String(value)&&node.querySelector('.coin-art'))return node;node.dataset.coinText=String(value);
  const mapping={'🟡':'beginner','🟣':'pro','🔴':'expert','🌐':'universal','🪙':'beginner'};
  node.replaceChildren(...String(value).split(/(🟡|🟣|🔴|🌐|🪙)/u).filter(Boolean).map(part=>mapping[part]?create(mapping[part]):document.createTextNode(part)));return node;
 }
 return{create,text};
})();
