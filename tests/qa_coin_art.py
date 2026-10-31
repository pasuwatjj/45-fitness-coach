"""Real local wallet and per-mode effects; disposable accounts, no production writes."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import time,hashlib
root='http://127.0.0.1:5055';out=Path('work/coin-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':950},reduced_motion='reduce');page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  assert c.request.post(root+'/auth/register',data={'email':f'coins{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
  token=c.request.post(root+'/session').json()['session_token'];response=c.request.post(root+'/profiles',headers={'X-Coach-Session':token},data={'name':'Coin'+str(time.time_ns())});assert response.ok;pid=response.json()['profile']['id']
  before=c.request.get(root+f'/profiles/{pid}/rewards',headers={'X-Coach-Session':token}).json();page.goto(root+'/45-fitness-coach');page.wait_for_timeout(900);page.evaluate("setTab('rewards')")
  page.wait_for_function("document.querySelectorAll('.training-wallet [data-artwork=ready]').length===4")
  cards=page.locator('.training-wallet>div');digests=[]
  for i,key in enumerate(['beginner','pro','expert','universal']):
   assert cards.nth(i).locator('.coin-art').get_attribute('data-currency')==key
   assert cards.nth(i).locator('strong').inner_text()==str(before['wallet'][key]);digests.append(hashlib.sha256(cards.nth(i).locator('.coin-art').screenshot()).hexdigest())
  assert len(set(digests))==4,'Atlas quadrants must look different'
  assert page.locator('.exchange-buttons .coin-art.universal').count()==3
  page.locator('.training-wallet').screenshot(path=str(out/f'{width}-wallet.png'))
  page.evaluate("document.body.dataset.theme='power'");page.locator('.training-wallet').screenshot(path=str(out/f'{width}-dark-wallet.png'))
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Mobile overflow'
  page.evaluate("()=>{setTab('workout');window.qaCamera=true;Object.defineProperty(BrowserCamera,'active',{get:()=>qaCamera});window.qaState={...fitnessState,running:false,difficulty:'beginner',person_count:1};Object.defineProperty(window,'fitnessState',{get:()=>qaState,set:()=>{},configurable:true});window.coachLandmarks={at:Date.now(),mirrored:false,points:Array.from({length:33},(_,i)=>[i===13?.35:.65,.55,1])}}")
  for key in ['beginner','pro','expert']:
   page.evaluate("key=>{document.querySelectorAll('.rep-coin').forEach(n=>n.remove());spawnCoachCoins('left','accepted',null,key)}",key)
   page.wait_for_selector('.rep-coin.accepted [data-artwork=ready]');assert page.locator('.rep-coin .coin-art').get_attribute('data-currency')==key
   page.locator('.rep-coin').screenshot(path=str(out/f'{width}-{key}-popup.png'))
  page.evaluate("document.querySelectorAll('.rep-coin').forEach(n=>n.remove());spawnCoachCoins('both','accepted','✓','pro')");assert page.locator('.rep-coin.accepted').count()==2
  page.evaluate("document.querySelectorAll('.rep-coin').forEach(n=>n.remove());spawnCoachCoins('right','rejected',null,'expert')");assert page.locator('.coin-shard .coin-art.expert').count()==2;page.locator('.rep-coin').screenshot(path=str(out/f'{width}-rejected.png'))
  if width==1280:
   page.emulate_media(reduced_motion='no-preference');page.evaluate("document.querySelectorAll('.rep-coin').forEach(n=>n.remove());spawnCoachCoins('right','rejected',null,'pro')");page.wait_for_timeout(220)
   assert page.locator('.coin-shard.left').evaluate('e=>getComputedStyle(e).transform')!='none'
   page.locator('.screen').screenshot(path=str(out/f'{width}-broken-effect.png'));page.emulate_media(reduced_motion='reduce')
  page.evaluate("document.querySelectorAll('.rep-coin').forEach(n=>n.remove());spawnCoachCoins('left','unverified')");assert page.locator('.rep-coin .coin-art').count()==0
  page.evaluate("for(let i=0;i<20;i++)spawnCoachCoins('left','accepted',null,'beginner')");assert page.locator('.rep-coin').count()<=8;page.wait_for_timeout(1450);assert page.locator('.rep-coin').count()==0
  # Cardio retains its existing gold reward type, even after an Expert workout.
  page.evaluate("qaCamera=false;qaState.difficulty='expert';setTab('cardio')");page.wait_for_selector('.cardio-screen')
  page.evaluate("qaState.cardio={id:'visual-only',reps:1,remaining:15,preparing:0,mode:'full',cue:'ready'};latestFrameState=null")
  page.wait_for_selector('.cardio-coin .coin-art[data-artwork=ready]');assert page.locator('.cardio-coin .coin-art').get_attribute('data-currency')=='beginner'
  # Cached atlas remains visible after re-entry and reload.
  page.evaluate("qaState.cardio=null;setTab('rewards')");page.wait_for_function("document.querySelectorAll('.training-wallet [data-artwork=ready]').length===4")
  after=c.request.get(root+f'/profiles/{pid}/rewards',headers={'X-Coach-Session':token}).json();assert after['wallet']==before['wallet'] and after['rates']==before['rates'] and after['history']==before['history']
  page.reload();page.wait_for_timeout(700);page.evaluate("setTab('rewards')");page.wait_for_function("document.querySelectorAll('.training-wallet [data-artwork=ready]').length===4")
  assert not errors,errors;c.close();print(width,'PASS wallet/atlas, mode-specific popups, paired/rejected/unclear feedback, cleanup, cardio gold, reload, unchanged balances/rates/history',flush=True)
 b.close()
