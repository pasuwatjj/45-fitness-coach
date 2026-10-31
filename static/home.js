'use strict';
(() => {
 const en=window.I18N?.lang==='en';
 const home=document.getElementById('homePage');
 const words=en?{tag:'YOUR EVERYDAY TRAINING CLUB',title:'45 FITNESS COACH',sub:'Move. Collect. Come back stronger.',intro:'Your camera, your plan, your small wins. Choose where to begin.',name:'Ready to train. Your last player name is selected automatically.',add:'My profile / edit name',train:'Exercise categories',desc:'Back · Arms · Chest · Shoulders · Legs',plan:'My training calendar',planSub:'Build your routine. Complete your daily sets.',rank:'The discipline leaderboard',rankSub:'Collect training days and keep your fire going.',health:'My health overview',healthSub:'Save your measurements and follow your progress.',choose:'Choose a muscle group',back:'Back',arms:'Arms',chest:'Chest',shoulders:'Shoulders',legs:'Legs'}:{tag:'พื้นที่ฝึกเล็ก ๆ ของเราในทุกวัน',title:'45 FITNESS COACH',sub:'ยกให้สนุก เก็บทุกความตั้งใจ',intro:'กล้องของเรา ตารางของเรา ค่อย ๆ แข็งแรงขึ้นด้วยกัน',name:'พร้อมเล่นได้เลย ระบบเลือกชื่อเดิมให้อัตโนมัติ',add:'โปรไฟล์ / เปลี่ยนชื่อของฉัน',train:'หมวดหมู่การออกกำลังกาย',desc:'หลัง · แขน · อก · ไหล่ · ขา',plan:'ปฏิทินออกกำลังกาย',planSub:'จัดตารางของเรา เล่นครบเซตแล้วเก็บไฟ',rank:'อันดับคนมีวินัย',rankSub:'สะสมวันฝึกตามแผน รักษาไฟให้ต่อเนื่อง',health:'ภาพรวมสุขภาพของฉัน',healthSub:'บันทึกค่าที่วัด แล้วติดตามการเปลี่ยนแปลง',choose:'เลือกกล้ามเนื้อที่อยากฝึก',back:'หลัง',arms:'แขน',chest:'อก',shoulders:'ไหล่',legs:'ขา'};
 home.setAttribute('data-i18n-ignore','');
 const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n};
 const hero=el('div',null,'home-hero');hero.append(el('span',words.tag,'home-tag'),el('h2',words.title),el('h3',words.sub),el('p',words.intro),el('span','✦  45  ✦','home-emblem'));home.append(hero);
 const brandBox=el('aside',null,'corner-brand');
 const brandButton=el('button',null,'brand-home');brandButton.type='button';brandButton.setAttribute('aria-label',en?'Back to home':'กลับหน้าหลัก');brandButton.onclick=()=>setTab('home');
 const brand=el('img');brand.src='/static/images/45-team-logo.png';brand.alt='45 Fitness Coach';brand.width=1536;brand.height=1024;brandButton.append(brand);brandBox.append(brandButton);
 const styleSwitch=document.querySelector('.theme-switch');
 if(styleSwitch)brandBox.append(styleSwitch);
 document.body.prepend(brandBox);
 const setup=el('div',null,'home-setup'),create=el('button',words.add,'secondary');setup.append(el('p',words.name),create);home.append(setup);
 create.onclick=()=>setTab('profile');
 const tiles=el('div',null,'home-tiles'),categories=el('section',null,'home-categories');categories.hidden=true;categories.append(el('h2',words.choose));
 function tile(title,sub,icon,fn,photo){const b=el('button',null,'home-tile');b.type='button';if(photo){const img=el('img');img.src=photo;img.alt='';img.loading='lazy';b.append(img)}const text=el('span',null,'home-tile-copy');text.append(el('span',icon,'home-tile-icon'),el('strong',title),el('small',sub));b.append(text);b.onclick=fn;tiles.append(b)}
 tile(words.train,words.desc,'🏋️',()=>{categories.hidden=!categories.hidden;if(!categories.hidden)categories.scrollIntoView({behavior:'smooth',block:'start'})},'/static/images/jeff/page-31.jpg');
 tile(en?'Cardio coin rush':'คาร์ดิโอเผาผลาญ · เกมเก็บเหรียญ',en?'15-second jumping jacks · two camera modes':'กระโดดตบ 15 วินาที · เต็มตัว / ครึ่งตัว','🪙',()=>setTab('cardio'));
 tile(words.plan,words.planSub,'▦',()=>setTab('calendar'));
 tile(words.rank,words.rankSub,'🔥',()=>setTab('leader'));
 tile(words.health,words.healthSub,'♡',()=>setTab('health'));
 tile(en?'Create character':'สร้างตัวละคร',en?'Your 3D character · grow through training':'ตัวละคร 3 มิติ · เติบโตจากการฝึก','◈',()=>window.CharacterPage.show());
 tile(en?'Redeem rewards':'แลกของรางวัล',en?'Exchange coins · VIP whey: 100 universal':'แลกเหรียญ · VIP แลกเวย์ 100 เหรียญสากล','🎁',()=>setTab('rewards'));
 tile(en?'Your inbox':'กล่องข้อความ',en?'Friends, reminders and a little encouragement':'แชตเพื่อน · เวลาเตือนฝึก · กำลังใจเล็ก ๆ','✉',()=>setTab('inbox'));tiles.lastElementChild.id='homeInboxTile';
 tile(en?'Administrator dashboard':'หลังบ้านแอดมิน',en?'Members · profiles · VIP':'สมาชิก · โปรไฟล์ · ให้ยศ VIP','🛡',()=>setTab('admin'));tiles.lastElementChild.dataset.adminOnly='';tiles.lastElementChild.hidden=true;
 home.append(tiles,categories);
 for(const group of ['back','arms','chest','shoulders','legs']){const box=el('details',null,'home-group');box.dataset.group=group;box.append(el('summary',words[group]));for(const ex of exerciseCatalog.filter(e=>e.group===group)){const b=el('button',null,'secondary'),title=el('span',ex.name,'exercise-choice-title');b.append(title);b.type='button';if(['supported_row','lying_triceps','incline_press','front_raise','split_squat'].includes(ex.id)){b.dataset.vipExercise=ex.id;title.textContent=ex.name+' · 🔒 VIP'}const preview=el('img');preview.src=ex.images[0];preview.alt=ex.name;preview.loading='lazy';preview.className='exercise-tile-image';b.prepend(preview);b.classList.add('exercise-choice');b.onclick=()=>{if(window.VIPPage&&!window.VIPPage.can(ex.id)){setTab('vip');return}setTab('workout');if(wasRunning){$('stop').scrollIntoView({block:'center'});return}$('exercise').value=ex.id;$('exercise').onchange();$('start').scrollIntoView({behavior:'smooth',block:'start'})};box.append(b)}categories.append(box)}
 $('homeTab').onclick=()=>setTab('home');
 setTab('home');
})();
