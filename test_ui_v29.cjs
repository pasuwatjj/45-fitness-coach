// Local DOM regressions: decoration must not disrupt actual controls or live page updates.
const {JSDOM}=require('jsdom'),fs=require('fs'),assert=require('assert'),{spawnSync}=require('child_process');
const rendered=spawnSync(process.env.PYTHON||'python',['-c',"import app; print(app.app.test_client().get('/').get_data(as_text=True))"],{cwd:__dirname,encoding:'utf8'});assert.equal(rendered.status,0,rendered.stderr);
const html=rendered.stdout.replace(/<script[\s\S]*?<\/script>/g,''),code=f=>fs.readFileSync(__dirname+'/static/'+f,'utf8'),tick=()=>new Promise(r=>setTimeout(r,10));
(async()=>{
for(const lang of ['th','en']){
 const d=new JSDOM(html,{url:'https://fitness.example',runScripts:'outside-only',pretendToBeVisual:true}),w=d.window;
 w.$=id=>w.document.getElementById(id);w.I18N={lang};w.exerciseCatalog=['back','arms','chest','shoulders','legs'].map(group=>({id:group,name:group,group,images:['/sample.svg']}));w.wasRunning=false;w.setTab=()=>{};
 w.eval(code('home.js'));
 const button=w.$('rewardsTab');let clicked=0;button.onclick=()=>clicked++;
 const ids=[...w.document.querySelectorAll('[id]')].map(n=>n.id);
 w.eval(code('themes-v29.js'));
 assert.equal(w.$('rewardsTab'),button);button.click();assert.equal(clicked,1);
 assert.deepEqual([...w.document.querySelectorAll('[id]')].map(n=>n.id),ids);
 for(const id of ['home','workout','calendar','leader','cardio','health','character','profile','vip','rewards','challenges','friends','admin'])assert(w.$(id+'Tab').dataset.themeIcon,id);
 assert.equal(w.document.querySelectorAll('.home-tile-icon[data-theme-icon]').length,8);
 assert.equal(w.document.querySelectorAll('.home-group summary[data-theme-icon]').length,5);
 assert.equal(w.document.querySelectorAll('.theme-garden').length,1);
 // A real existing module can replace a live account button label, including badges/counts.
 w.$('friendsTab').textContent=lang==='en'?'👥 Friends · 📥 17':'👥 เพื่อน · 📥 17';
 const h=w.document.createElement('h2');h.textContent=lang==='en'?'🎁 Redeem rewards':'🎁 แลกของรางวัล';w.$('rewardsPage').append(h);
 const chat=w.document.createElement('dialog');chat.className='friend-chat';chat.innerHTML='<h3>Chat with a friend</h3>';w.document.body.append(chat);
 await tick();assert.equal(w.$('friendsTab').dataset.themeIcon,'friends');assert(w.$('friendsTab').textContent.includes('17'));assert.equal(h.dataset.themeIcon,'rewards');assert.equal(chat.querySelector('h3').dataset.themeIcon,'chat');
 const after=w.FitnessThemes.passes;await tick();await tick();assert.equal(w.FitnessThemes.passes,after,'observer must settle without a self-trigger cycle');
 for(let i=0;i<10;i++)w.FitnessThemes.refresh();assert.equal(w.document.querySelectorAll('.theme-garden').length,1);assert.equal(w.$('rewardsTab'),button);button.click();assert.equal(clicked,2);
 // Use the existing application theme switch to verify actual persistence and pressed states.
 w.remember=(k,v)=>w.localStorage.setItem(k,v);w.setText=(id,text)=>w.$(id).textContent=text;
 const app=code('app.js');w.eval(app.slice(app.indexOf('function setTheme('),app.indexOf("$('powerTheme').onclick")));
 for(const theme of ['power','spicy']){w.setTheme(theme);assert.equal(w.document.body.dataset.theme,theme);assert.equal(w.localStorage.getItem('45-theme'),theme);assert.equal(w.$(theme+'Theme').getAttribute('aria-pressed'),'true');assert(w.$(theme+'Theme').classList.contains('theme-sticker'));assert.equal(w.$((theme==='power'?'spicy':'power')+'Theme').getAttribute('aria-pressed'),'false')}
 await tick();assert.equal(w.document.querySelectorAll('.theme-garden').length,1);
 w.eval(app.slice(app.indexOf('function setTab('),app.indexOf("$('workoutTab').onclick")));
 for(const page of ['home','rewards','vip','character','profile','friends','cardio']){w.setTab(page);for(const id of ['homeTab','rewardsTab','profileTab','vipTab'])assert(w.$(id).classList.contains('theme-sticker'),'page switch preserves '+id)}
 // Camera/status text updates are deliberately not decoration work.
 const before=w.FitnessThemes.passes;for(let i=0;i<40;i++)w.$('status').textContent='Frame '+i;await tick();assert.equal(w.FitnessThemes.passes,before);
 d.window.close();
}
console.log('PASS v29 TH/EN: 13 page actions, 8 home tiles, 5 category icons, dynamic account badges/page/chat, control IDs/listeners preserved, singleton hero art, observer settles, camera updates ignored, existing theme persistence/pressed states');
const css=code('theme-icons-v29.css')+code('themes-v29.css');
const urls=[...css.matchAll(/url\(['"]?(\/static\/[^)'" ]+)['"]?\)/g)].map(m=>m[1]);assert.equal(urls.length,44);
for(const url of urls){assert(url.endsWith('?v=29'));const file=__dirname+url.split('?')[0];assert(fs.existsSync(file),url);assert(fs.readFileSync(file,'utf8').includes('<svg'))}
assert(!/https?:\/\//.test(code('themes-v29.js')+css));assert(css.includes('prefers-reduced-motion'));assert(code('v28.css').includes('.brand-motion { display:none !important; }'));
console.log('PASS v29: all 42 original SVG files exist (44 local CSS references), no CDN dependency, reduced-motion rule and removed decoration stay hidden');
})().catch(e=>{console.error(e);process.exit(1)});
