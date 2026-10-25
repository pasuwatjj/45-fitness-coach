'use strict';
window.AdminManagement=(()=>{
 const en=window.I18N?.lang==='en',t=(th,eng)=>en?eng:th;
 const el=(tag,text='')=>{const n=document.createElement(tag);n.textContent=text;return n};
 async function api(url,data){const r=await fetch(url,data===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const d=await r.json();if(!r.ok){const parts=String(d.error||'Request failed').split(' / ');const e=Error(parts.length===2?(en?parts[0]:parts[1]):parts[0]);e.definitive=r.status>=400&&r.status<500;throw e;}return d}
 const labels={beginner:t('🟡 มือใหม่','🟡 Beginner'),pro:t('🟣 โปร','🟣 Pro'),expert:t('🔴 ผู้เชี่ยวชาญ','🔴 Expert'),universal:t('🌐 สากล','🌐 Universal')};
 function field(box,label,node){const l=el('label',label);l.style.display='block';l.append(node);box.append(l);node.style.cssText='display:block;max-width:100%;width:100%;box-sizing:border-box';return node}
 function button(text,run){const b=el('button',text);b.type='button';b.className='secondary';b.onclick=run;return b}
 async function member(account,parent){
  const box=el('details');box.className='admin-management';box.append(el('summary',t('จัดการเหรียญ / ระงับบัญชี','Manage coins / suspend account')));parent.append(box);
  let loaded=false;box.addEventListener('toggle',async()=>{if(!box.open||loaded)return;loaded=true;const status=el('p');status.setAttribute('role','status');box.append(status);try{
   const data=await api('/admin/accounts/'+account.id+'/wallets'),profile=field(box,t('โปรไฟล์ผู้รับ','Recipient profile'),el('select'));
   for(const p of data.profiles){const o=el('option',p.name+' (#'+p.id+')');o.value=p.id;profile.append(o)}
   const balance=el('p');box.append(balance);const refresh=async()=>{const d=await api('/admin/accounts/'+account.id+'/wallets');const p=d.profiles.find(p=>p.id===Number(profile.value));balance.textContent=p?Object.entries(p.wallet).map(([k,v])=>labels[k]+': '+v.toLocaleString()).join(' · '):t('ไม่มีโปรไฟล์','No profiles');};profile.onchange=refresh;await refresh();
   const currency=field(box,t('ชนิดเหรียญ','Currency'),el('select'));for(const[k,v]of Object.entries(labels)){const o=el('option',v);o.value=k;currency.append(o)}
   const direction=field(box,t('เพิ่มหรือลด','Add or subtract'),el('select'));for(const[v,txt]of [['1',t('เพิ่ม','Add')],['-1',t('ลด','Subtract')]]){const o=el('option',txt);o.value=v;direction.append(o)}
   const amount=field(box,t('จำนวนเต็ม 1–1,000,000','Whole amount 1–1,000,000'),el('input'));amount.type='number';amount.min='1';amount.max='1000000';amount.step='1';amount.value='1';
   const reason=field(box,t('เหตุผล (จำเป็น)','Reason (required)'),el('textarea'));reason.maxLength=500;
   let pending=null;
   async function change(action,payload){
    if(!reason.value.trim())throw Error(t('กรุณาระบุเหตุผล','Please enter a reason'));
    const body={...payload,reason:reason.value.trim()},signature=JSON.stringify({action,body});
    if(pending?.completed&&pending.signature!==signature)pending=null;
    if(pending&&pending.signature!==signature)throw Error(t('โปรดลองคำขอเดิมอีกครั้งก่อนเปลี่ยนข้อมูล','Retry the pending request before changing its details'));
    pending??={signature,key:crypto.randomUUID()};
    try{const d=await api('/admin/accounts/'+account.id+'/'+action,{...body,request_id:pending.key});pending.completed=true;status.textContent=t('สำเร็จ: ','Saved: ')+d.audit.before_value+' → '+d.audit.after_value+' · '+new Date(d.audit.created*1000).toLocaleString();try{await refresh()}catch(e){status.textContent+=' · '+t('รีเฟรชหน้าเพื่อดูยอดล่าสุด','Refresh the page to see the latest balance')}return d}catch(e){if(e.definitive)pending=null;throw e}
   }
   const submit=button(t('บันทึกการปรับเหรียญ','Save coin adjustment'),async()=>{submit.disabled=true;try{const n=Number(amount.value);if(!Number.isSafeInteger(n)||n<1||n>1000000)throw Error(t('จำนวนไม่ถูกต้อง','Invalid amount'));await change('coins',{target_profile_id:Number(profile.value),currency:currency.value,amount:n*Number(direction.value)})}catch(e){status.textContent=e.message}finally{submit.disabled=!data.profiles.length}});submit.disabled=!data.profiles.length;box.append(submit);
   let banned=data.banned;const ban=button('',async()=>{ban.disabled=true;try{await change('ban',{banned:!banned});banned=!banned;labelBan()}catch(e){status.textContent=e.message}finally{ban.disabled=false}});function labelBan(){ban.textContent=banned?t('ยกเลิกระงับบัญชี','Unsuspend account'):t('ระงับบัญชี','Suspend account')}labelBan();box.append(ban);
  }catch(e){status.textContent=e.message;loaded=false}});
 }
 function history(parent){const box=el('details');box.className='panel';box.append(el('summary',t('ประวัติปรับเหรียญ / ระงับบัญชี / แลกเหรียญทั้งระบบ','Coin adjustments / suspensions / serverwide exchanges')));parent.append(box);const list=el('div'),status=el('p');let page=1;const type=field(box,t('ประเภทประวัติ','History type'),el('select'));for(const[v,txt]of [['management',t('การจัดการของแอดมิน','Administrator actions')],['exchange',t('การแลกเหรียญจริง','Actual exchanges')]]){const o=el('option',txt);o.value=v;type.append(o)}const prev=button(t('ก่อนหน้า','Previous'),()=>{page--;load()}),next=button(t('ถัดไป','Next'),()=>{page++;load()});box.append(button(t('รีเฟรช','Refresh'),()=>load()),status,list,prev,next);type.onchange=()=>{page=1;load()};async function load(){try{const d=await api('/admin/'+type.value+'-history?page='+page);list.replaceChildren();status.textContent=t('หน้า ','Page ')+page;prev.disabled=page===1;next.disabled=d.history.length<50;for(const r of d.history){const row=el('p');row.style.overflowWrap='anywhere';row.textContent=type.value==='exchange'?`${new Date(r.created*1000).toLocaleString()} · ${r.email||r.owner} · ${r.name} (#${r.profile_id}) · ${labels[r.currency]} −${r.spent} → ${labels.universal} +${r.received} · ${r.id}`:`${new Date(r.created*1000).toLocaleString()} · ${r.actor_email} → ${r.target_email} · ${r.profile_name||''} ${r.profile?'(#'+r.profile+')':''} · ${r.action==='coins'?labels[r.currency]+' '+(r.amount>0?'+':'')+r.amount:t('ระงับบัญชี 0=ไม่ระงับ 1=ระงับ','Suspension 0=active 1=suspended')} · ${r.before_value} → ${r.after_value} · ${r.reason}`;list.append(row)}if(!d.history.length)list.append(el('p',t('ไม่มีรายการ','No entries')))}catch(e){status.textContent=e.message}}box.addEventListener('toggle',()=>{if(box.open)load()})}
 return{member,history};
})();
