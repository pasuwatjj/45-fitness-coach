/* Run after page modules: direct links and actionable incomplete-upload diagnosis. */
'use strict';
(()=>{
 const en=window.I18N?.lang==='en',expected=['RewardsPage','VIPPage','CharacterPage','FitnessCharacterRenderer'];
 const missing=expected.filter(name=>!window[name]);
 for(const name of ['character','rewards','vip'])if(!document.getElementById(name+'Page')||!document.getElementById(name+'Tab'))missing.push(name+' HTML');
 if(missing.length){const note=document.createElement('p');note.id='appLoadNotice';note.setAttribute('role','alert');note.textContent=(en?'Some website files are missing or from different versions. Upload the complete v30 folder, restart Python, then reload: ':'ไฟล์เว็บไม่ครบหรือคนละรุ่น กรุณาอัปโหลดโฟลเดอร์ v30 ทั้งชุด รีสตาร์ต Python แล้วโหลดใหม่: ')+missing.join(', ');document.getElementById('mainApp').prepend(note)}
 const route=()=>{const key=location.hash.slice(1);if(['character','rewards','vip','profile'].includes(key))setTab(key)};
 window.addEventListener('hashchange',route);route();
})();
