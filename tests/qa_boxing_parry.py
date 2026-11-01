"""Real local two-account match: dash parry, glass cue and immediate counter input."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os,time
root=os.environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5070');assert root.startswith('http://127.0.0.1:')
out=Path('work/boxing-bots-review');out.mkdir(parents=True,exist_ok=True)
def account(c):
 assert c.request.post(root+'/auth/register',data={'email':f'parry{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
 h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']}
 pid=c.request.post(root+'/profiles',headers=h,data={'name':'Parry '+str(time.time_ns())[-5:]}).json()['profile']['id']
 assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{}}).ok
 uid=c.request.get(root+'/social/me',headers=h).json()['account_id'];return uid,pid,h
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 ca=b.new_context(viewport={'width':1100,'height':850});cb=b.new_context();uid,pid,h=account(ca);oid,opid,oh=account(cb)
 ca.request.post(root+'/social/friends',headers=h,data={'action':'request','account_id':oid});cb.request.post(root+'/social/friends',headers=oh,data={'action':'accept','account_id':uid})
 m=ca.request.post(root+'/social/boxing/invite',headers=h,data={'friend':oid,'profile':pid,'control_mode':'computer'}).json();mid=m['id']
 cb.request.post(root+'/social/boxing/'+mid,headers=oh,data={'action':'accept','profile':opid});cb.request.post(root+'/social/boxing/'+mid,headers=oh,data={'action':'ready'})
 p=ca.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(root+'/45-fitness-coach?lang=en');p.locator('#homeBoxingTile').click();p.wait_for_function("!document.querySelector('[data-mode=friends]').disabled")
 p.locator('[data-mode=friends]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-primary').click();p.get_by_role('button',name='Return to match',exact=True).click()
 p.wait_for_function("Boxing.state?.status==='active'",timeout=15000);p.wait_for_function('Boxing.world?.actors.every(a=>a.body)',timeout=60000)
 p.evaluate("const draw=Boxing.world.renderer.render.bind(Boxing.world.renderer);let last=0;Boxing.world.renderer.render=(...args)=>{if(performance.now()-last>80){last=performance.now();draw(...args)}};window.parryCueSeen=false;new MutationObserver(()=>{if(!document.querySelector('.boxing-parry-frame').hidden)parryCueSeen=true}).observe(document.querySelector('.boxing-parry-frame'),{attributes:true});void 0")
 # No fixture combat state: the opponent's authenticated attack arrives over the real API.
 r=cb.request.post(root+'/social/boxing/'+mid,headers=oh,data={'action':'left','seq':1,'input_source':'keyboard','strike_id':'qa-incoming','punch_type':'straight'});assert r.ok,r.text()
 p.keyboard.down('d');p.keyboard.down('Control');p.wait_for_function('parryCueSeen',timeout=3000)
 p.keyboard.up('d');p.keyboard.press('q');p.keyboard.up('Control')
 p.wait_for_function("Boxing.state.events?.some(e=>e.counter)||Boxing.state.pending_strikes?.some(e=>e.counter)",timeout=3000)
 assert p.evaluate("Boxing.state.events.some(e=>e.result==='parry')&&Boxing.state.players[0].hp===10")
 p.wait_for_function("document.querySelector('.boxing-parry-frame').hidden",timeout=2000)
 # Replay only the public visual cue for a stable screenshot after real combat assertions.
 p.evaluate("const cue=document.querySelector('.boxing-parry-frame').cloneNode(true);cue.hidden=false;cue.classList.remove('active');document.querySelector('.boxing-arena').append(cue)")
 p.locator('.boxing-arena').screenshot(path=str(out/'parry-glass.png'))
 p.locator('.boxing-back').click();assert not errors,errors
 print('PASS authenticated incoming punch, real Ctrl+D opposite-side parry, glass cue, Q counter while Ctrl held, zero damage and cue expiry; no browser errors')
 b.close()
