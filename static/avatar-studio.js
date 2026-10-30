'use strict';
window.AvatarStudio=(()=>{
 const t=(th,en)=>window.I18N?.lang==='en'?en:th;
 const el=(tag,text='',cls='')=>{const n=document.createElement(tag);n.textContent=text;n.className=cls;return n};
 let renderer=null,serial=0,abort=null;
 const current=()=>document.getElementById('profile')?.value||window.fitnessState?.profile?.id;
 function leave(){serial++;abort?.abort();renderer?.destroy();renderer=null}
 async function open(pid=current(),demo=null){
  leave();const generation=serial,page=document.getElementById('characterPage');if(!page)return;
  page.dataset.i18nIgnore='';page.replaceChildren(el('p',t('กำลังเปิดห้องแต่งตัว…','Opening avatar studio…')));
  if(!pid&&!demo){page.replaceChildren(el('p',t('เลือกโปรไฟล์ก่อนสร้างตัวละคร','Select a profile first')));return}
  abort=new AbortController();let model;
  try{if(demo)model=structuredClone(demo);else{await window.ensureFitnessSession?.();const r=await fetch('/profiles/'+pid+'/character',{cache:'no-store',signal:abort.signal});model=await r.json();if(!r.ok)throw Error(model.error||'Cannot load avatar')}}catch(e){if(generation===serial&&e.name!=='AbortError')page.replaceChildren(el('p',e.message));return}
  if(generation!==serial)return;
  const a=model.appearance={eyes:'almond',nose:'straight',eye_color:'#553521',face:'soft',build:.45,...model.appearance};
  const title=el('header','','studio-title');title.append(el('small','45 / AVATAR STUDIO'),el('h1',t('ตัวละครของคุณ','Made to be you')),el('p',t('ปรับรูปร่าง ใบหน้า และสไตล์ในแบบของคุณ','Shape, face and style — make it yours.')));
  const layout=el('div','','studio-layout'),stage=el('section','','studio-stage'),canvas=el('canvas');canvas.width=720;canvas.height=840;canvas.setAttribute('aria-label',t('ตัวละครสามมิติ ลากหรือใช้ปุ่มลูกศรเพื่อหมุน','3D avatar. Drag or use arrow keys to rotate'));
  const badge=el('span',t('ดูได้รอบตัว · 3D','360° / 3D'),'studio-badge'),hint=el('p',t('ลากเพื่อหมุน · ← →','Drag to rotate · ← →'),'studio-hint');
  stage.append(badge,canvas,hint);
  const actions=el('div','','studio-view');for(const [label,yaw]of [[t('ด้านหน้า','Front'),0],[t('ด้านข้าง','Side'),1.57],[t('ด้านหลัง','Back'),3.14]]){const b=el('button',label);b.type='button';b.onclick=()=>{renderer.yaw=yaw;renderer.draw()};actions.append(b)}stage.append(actions);
  const form=el('form','','studio-form'),note=el('p','','studio-status');note.setAttribute('role','status');
  function group(n,title){const section=el('fieldset'),legend=el('legend',n+' / '+title);section.append(legend);form.append(section);return section}
  const body=group('01',t('รูปร่างจากโปรไฟล์','Profile & silhouette')),face=group('02',t('รายละเอียดใบหน้า','Face details')),style=group('03',t('ผมและสี','Hair & colors'));
  function select(parent,label,key,options){const l=el('label',label),s=el('select');s.name=key;for(const [v,name]of options){const o=el('option',name);o.value=v;s.append(o)}s.value=a[key];s.onchange=()=>{a[key]=s.value;update()};l.append(s);parent.append(l);return s}
  select(body,t('ลักษณะตัวละคร','Character'), 'gender',[['male',t('ชาย','Male')],['female',t('หญิง','Female')]]);
  const dims={...model.dimensions};const dimensionInputs={};
  for(const [key,label,min,max,fallback]of [['height_cm',t('ส่วนสูง (ซม.)','Height (cm)'),50,250,170],['weight_kg',t('น้ำหนัก (กก.)','Weight (kg)'),5,350,65]]){const l=el('label',label),input=el('input');input.type='number';input.name=key;input.min=min;input.max=max;input.step='.1';input.required=true;input.value=dims[key]??'';input.placeholder=String(fallback);dimensionInputs[key]=input;l.append(input);body.append(l);input.oninput=()=>{if(input.validity.valid){dims[key]=Number(input.value);update()}}}
  const buildLabel=el('label',t('ความกำยำที่ชอบ (สไตล์ตัวละคร)','Muscularity preference (visual style)')),range=el('input');range.type='range';range.name='build';range.min=0;range.max=1;range.step='.05';range.value=a.build;range.oninput=()=>{a.build=Number(range.value);update()};buildLabel.append(range);body.append(buildLabel);
  body.append(el('small',t('น้ำหนักและส่วนสูงช่วยปรับความอวบโดยประมาณ ไม่ใช่การสแกนร่างกายหรือการวัดกล้ามเนื้อ','Weight and height guide fullness. This is not a body scan or a muscle measurement.')));
  select(face,t('ทรงหน้า','Face'),'face',[['soft',t('นุ่มมน','Soft')],['angular',t('กรามชัด','Angular')]]);
  select(face,t('ดวงตา','Eyes'),'eyes',[['almond',t('อัลมอนด์','Almond')],['round',t('กลม','Round')],['narrow',t('เรียว','Narrow')]]);
  select(face,t('จมูก','Nose'),'nose',[['straight',t('สันตรง','Straight')],['rounded',t('ปลายมน','Rounded')],['broad',t('ฐานกว้าง','Broad')]]);
  select(style,t('ทรงผม','Hair'),'hair',[['short',t('สั้น','Short')],['swept',t('ปัดข้าง','Swept')],['curly',t('หยิก','Curly')],['bob',t('บ๊อบ','Bob')],['ponytail',t('หางม้า','Ponytail')],['bald',t('ไม่มีผม','Bald')]]);
  for(const [parent,key,label]of [[face,'eye_color',t('สีตา','Eyes')],[style,'skin_color',t('สีผิว','Skin')],[style,'hair_color',t('สีผม','Hair')],[style,'shorts_color',t('กางเกง','Shorts')]]){const l=el('label',label),c=el('input');c.type='color';c.name=key;c.value=a[key];c.oninput=()=>{a[key]=c.value;update()};l.append(c);parent.append(l)}
  const save=el('button',demo?t('โหมดตัวอย่าง · ไม่บันทึกเข้าบัญชี','Preview only — no account save'):t('บันทึกตัวละครและข้อมูลโปรไฟล์','Save avatar & profile'),'studio-save');save.type='submit';if(demo)save.disabled=true;
  form.append(save,note);layout.append(stage,form);page.replaceChildren(title,layout);
  renderer=new FitnessCharacterRenderer(canvas);
  function update(){const h=Number(dimensionInputs.height_cm.value),w=Number(dimensionInputs.weight_kg.value);if(h>=50&&h<=250&&w>=5&&w<=350){const fullness=Math.max(0,Math.min(1,(w/(h/100)**2-18.5)/18));model.visual={...model.visual,fullness,height_scale:Math.max(.88,Math.min(1.12,h/170)),has_dimensions:true}}
   renderer.set(model);if(canvas.dataset.renderer==='fallback')note.textContent=t('อุปกรณ์นี้ใช้ภาพสำรอง เพราะเปิดกราฟิก 3D ไม่ได้','This device uses fallback graphics because 3D is unavailable.');}
  update();renderer.start();
  form.onsubmit=async e=>{e.preventDefault();if(demo||!form.reportValidity())return;save.disabled=true;note.textContent=t('กำลังบันทึก…','Saving…');try{const r=await fetch('/profiles/'+pid+'/character',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({appearance:a,dimensions:{height_cm:Number(dimensionInputs.height_cm.value),weight_kg:Number(dimensionInputs.weight_kg.value)}})});const data=await r.json();if(!r.ok)throw Error(data.error||'Save failed');if(generation!==serial)return;model=data;renderer.set(model);note.textContent=t('บันทึกแล้ว ✓ เปิดอีกครั้งจะใช้ตัวละครนี้','Saved ✓ Your character is ready.');window.dispatchEvent(new Event('fitness-profile-updated'))}catch(e){if(generation===serial)note.textContent=e.message}finally{if(generation===serial)save.disabled=false}};
 }
 return{open,leave};
})();
// Keep the existing member-profile flow. Only the owner's editor is replaced.
if(window.CharacterPage){const original=window.CharacterPage;window.CharacterPage={...original,open(id,member){if(member)return original.open(id,member);return AvatarStudio.open(id||undefined)},leave(){AvatarStudio.leave();original.leave?.()}}}
