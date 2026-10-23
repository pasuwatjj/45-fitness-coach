'use strict';
const nativeFetch=window.fetch.bind(window);
async function originalFetch(input,options={}){
 const controller=new AbortController(),abort=()=>controller.abort();let timer;
 if(options.signal?.aborted)controller.abort();else options.signal?.addEventListener('abort',abort,{once:true});
 try{return await Promise.race([nativeFetch(input,{...options,signal:controller.signal}),new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(Error('Connection timed out / การเชื่อมต่อหมดเวลา'))},20000)})])}
 finally{clearTimeout(timer);options.signal?.removeEventListener('abort',abort)}
}
let fitnessToken='',sessionFlight=null;
window.coachRevision=0;
let resolveSession;
const sessionReady=new Promise(resolve=>{resolveSession=resolve});
const accountText=(th,en)=>window.I18N?.lang==='en'?en:th;
window.FitnessAccount={guest:true,email:null};
async function enterAccount(){
 if(sessionFlight)return sessionFlight;
 sessionFlight=(async()=>{
  const response=await originalFetch('/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({auto_profile:true})});
  const data=await response.json();if(!response.ok)throw Error(data.error||'Cannot open session');
  fitnessToken=data.session_token;window.FitnessAccount={guest:!!data.guest,email:data.email};
  window.defaultFitnessProfile=data.default_profile?.id;
  document.getElementById('accountEmail').textContent=data.guest?accountText('ผู้เยี่ยมชม','Guest'):data.email;
  document.getElementById('logout').hidden=!!data.guest;
  document.getElementById('accountTab').textContent=data.guest?accountText('👤 สร้างบัญชี / เข้าสู่ระบบ','👤 Create account / Sign in'):accountText('🔐 บัญชี / เลขที่ชอบ','🔐 Account / Recovery');
  document.getElementById('mainApp').hidden=false;
  resolveSession(data);return data;
 })();
 try{return await sessionFlight}finally{sessionFlight=null}
}
window.fetch=async(input,options={})=>{
 const url=new URL(typeof input==='string'?input:input.url,location.href);
 if(url.origin!==location.origin)return originalFetch(input,options);
 await sessionReady;
 const headers=new Headers(options.headers||(input instanceof Request?input.headers:undefined));
 const sentToken=fitnessToken;headers.set('X-Coach-Session',sentToken);
 const response=await originalFetch(input,{...options,headers});
 // A failed background request must never close a newer workout or session.
 if(response.status===401&&sentToken===fitnessToken)document.getElementById('status').textContent=accountText('เซสชันหมดอายุ กดเริ่มอีกครั้งเพื่อเชื่อมต่อใหม่','Session expired. Press Start again to reconnect.');
 return response;
};
window.ensureFitnessSession=async()=>{
 await sessionReady;
 const r=await originalFetch('/status',{headers:{'X-Coach-Session':fitnessToken},cache:'no-store'});
 if(r.status===401){await enterAccount();window.coachRevision++;window.latestFrameState=null;if(typeof loadProfiles==='function')await loadProfiles()}
 else if(!r.ok)throw Error(accountText('เชื่อมต่อไม่ได้ ลองใหม่อีกครั้ง','Connection unavailable. Please retry.'));
};
(()=>{
 const el=id=>document.getElementById(id),form=el('authForm');let mode='login',ticket='',working=false;
 const t=accountText;
 function show(next='login'){
  mode=next;el('authPage').hidden=false;el('authStatus').textContent='';
  const titles={login:t('เข้าสู่ระบบ','Sign in'),register:t('สร้างบัญชีของคุณ','Create your account'),forgot:t('ลืมรหัสผ่าน','Forgot password'),reset:t('ตั้งรหัสผ่านใหม่','Reset password'),setup:t('ตั้ง / เปลี่ยนเลขที่ชอบ','Set / change favorite number')};
  el('authTitle').textContent=titles[mode];
  const visible={authEmail:['login','register','forgot'],authPassword:['login','register','reset','setup'],authConfirm:['register','reset'],authRecovery:['register','setup']};
  for(const [id,modes] of Object.entries(visible)){const on=modes.includes(mode);el(id).closest('.auth-field').hidden=!on;el(id).disabled=!on;el(id).required=on;el(id).value=''}
  el('authPassword').autocomplete=['register','reset'].includes(mode)?'new-password':'current-password';
  el('authSubmit').textContent=mode==='forgot'?t('ส่งลิงก์รีเซ็ตไปยังอีเมล','Email reset link'):mode==='setup'?t('บันทึกเลขที่ชอบ','Save favorite number'):titles[mode];
  el('authMode').hidden=!['login','register'].includes(mode);el('authMode').textContent=mode==='register'?t('มีบัญชีแล้ว · เข้าสู่ระบบ','Already registered? Sign in'):t('ยังไม่มีบัญชี · สมัครสมาชิก','New here? Create account');
  el('forgotPassword').hidden=!['login','register'].includes(mode);
  el('authRecoveryNote').hidden=!['register','forgot','setup'].includes(mode);
  el('authContext').textContent=mode==='setup'?t('กรอกรหัสผ่านปัจจุบันเพื่อเปลี่ยนเลขที่ชอบ','Enter your current password to change the favorite number'):t('เล่นแบบผู้เยี่ยมชมได้ สมัครเพื่อใช้บัญชีบนหลายอุปกรณ์และสมัคร VIP','You can train as a guest. Create an account for multiple devices and VIP.');
 }
 window.openFitnessAccount=()=>show(window.FitnessAccount.guest?'login':'setup');
 el('accountTab').onclick=window.openFitnessAccount;el('closeAuth').onclick=()=>{el('authPage').hidden=true;ticket='';form.reset()};
 el('authMode').onclick=()=>show(mode==='register'?'login':'register');el('forgotPassword').onclick=()=>show('forgot');
 form.onsubmit=async e=>{
  e.preventDefault();if(working||!form.reportValidity())return;
  const password=el('authPassword').value;
  if(['register','reset'].includes(mode)&&password!==el('authConfirm').value){el('authStatus').textContent=t('รหัสผ่านไม่ตรงกัน','Passwords do not match');return}
  working=true;el('authSubmit').disabled=true;
  const current=mode,path={login:'/auth/login',register:'/auth/register',forgot:'/auth/recovery/verify',reset:'/auth/recovery/reset',setup:'/auth/recovery/setup'}[mode];
  try{
   if(['register','login'].includes(current)&&typeof BrowserCamera!=='undefined'&&BrowserCamera.active){
    leaveWorkout();await originalFetch('/stop',{method:'POST',headers:{'X-Coach-Session':fitnessToken}});
   }
   const r=await originalFetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:el('authEmail').value,password,recovery_number:el('authRecovery').value,ticket})});
   const data=await r.json();if(!r.ok)throw Error(data.error||'Please retry');
   if(current==='forgot'){el('authStatus').textContent=data.message}
   else if(current==='reset'){ticket='';show('login');el('authStatus').textContent=t('ตั้งรหัสใหม่แล้ว เข้าสู่ระบบได้เลย','Password changed. Sign in with your new password.')}
   else if(current==='setup'){form.reset();el('authStatus').textContent=t('บันทึกเลขที่ชอบแล้ว','Favorite number saved.')}
   else{if(typeof leaveWorkout==='function')leaveWorkout();location.reload()}
  }catch(error){el('authStatus').textContent=error.message}finally{working=false;el('authSubmit').disabled=false}
 };
 el('logout').onclick=async()=>{leaveWorkout();try{await originalFetch('/auth/logout',{method:'POST'});location.reload()}catch(e){el('status').textContent=t('ออกจากระบบไม่ได้ ลองใหม่','Could not sign out. Please retry.')}};
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!el('authPage').hidden)el('closeAuth').click()});
 const resetToken=new URLSearchParams(location.hash.slice(1)).get('reset');
 if(resetToken&&/^[A-Za-z0-9_-]{43}$/.test(resetToken)){ticket=resetToken;history.replaceState(null,'',location.pathname+location.search);show('reset')}
 enterAccount().catch(e=>{el('status').textContent=t('เชื่อมต่อไม่ได้ กดรีเฟรชเมื่อเซิร์ฟเวอร์พร้อม','Connection unavailable. Refresh when the server is ready.');el('mainApp').hidden=false});
})();
