"""Local two-account admin room: V slow motion, guest belt and consented rematch."""
import os,time,sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];dbpath=os.environ['BOXING_TEST_DB'];assert root.startswith('http://127.0.0.1:') and dbpath.startswith('/tmp/')
out=Path('work/boxing-special-review');out.mkdir(parents=True,exist_ok=True)
def account(c,name):
    assert c.request.post(root+'/auth/register',data={'email':f'skill{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
    h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']}
    pid=c.request.post(root+'/profiles',headers=h,data={'name':name+' '+str(time.time_ns())[-6:]}).json()['profile']['id'];assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{}}).ok
    return c.request.get(root+'/social/me',headers=h).json()['account_id'],pid,h
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-background-timer-throttling','--disable-renderer-backgrounding'])
    a=b.new_context(viewport={'width':1200,'height':950});g=b.new_context(viewport={'width':1200,'height':950});uid,pid,h=account(a,'Admin');gid,gpid,gh=account(g,'Guest winner')
    a.request.post(root+'/social/friends',headers=h,data={'action':'request','account_id':gid});g.request.post(root+'/social/friends',headers=gh,data={'action':'accept','account_id':uid})
    with sqlite3.connect(dbpath) as db:db.execute("INSERT INTO account_roles(account_id,role) VALUES(?,'admin')",(uid,))
    m=a.request.post(root+'/social/boxing/invite',headers=h,data={'profile':pid,'friend':gid,'control_mode':'computer','custom_settings':{'hp':50,'armor':10,'level':3}}).json();mid=m['id'];assert g.request.post(root+'/social/boxing/'+mid,headers=gh,data={'action':'accept','profile':gpid}).ok
    pages=[a.new_page(),g.new_page()];errors=[]
    for p in pages:
        p.on('pageerror',lambda e:errors.append(str(e)));p.goto(root+'/45-fitness-coach?lang=en');p.locator('#homeBoxingTile').click();p.wait_for_function("!document.querySelector('[data-mode=friends]').disabled")
        p.locator('[data-mode=friends]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-primary').click();p.get_by_role('button',name='Return to match',exact=True).click()
    host,guest=pages
    for p in pages:
        p.wait_for_function("Boxing.state?.status==='active'",timeout=20000);p.wait_for_function('Boxing.world?.actors.every(a=>a.body)',timeout=60000)
        p.evaluate("const original=Boxing.world.renderer.render.bind(Boxing.world.renderer);let last=0;Boxing.world.renderer.render=(...args)=>{if(performance.now()-last>100){last=performance.now();original(...args)}};void 0")
    # Defender plays native targets; the attacker sees a spectator view.
    host.bring_to_front();host.locator('.cage-canvas').click();host.keyboard.press('x')
    for p in pages:p.wait_for_function("Boxing.state.special?.phase==='aim'&&Boxing.world.timeStopped")
    start=host.evaluate('Boxing.state.special.started_at');deadline=host.evaluate('Boxing.state.players[0].special_ready_at')
    assert abs(deadline-start-180)<.01
    assert host.evaluate('Boxing.state.special.damage')==25
    assert host.locator('.boxing-aim-target').is_disabled()
    assert guest.locator('.boxing-aim-target').is_enabled()
    assert guest.locator('.boxing-fighters').evaluate("e=>getComputedStyle(e).filter").startswith('grayscale(1)')
    # Scene transform and renderer frame counter must remain fixed while aim runs.
    frozen=guest.evaluate('({frame:Boxing.world.renderer.info.render.frame,x:Boxing.world.actors[1].body.position.x})')
    guest.wait_for_timeout(150)
    assert frozen==guest.evaluate('({frame:Boxing.world.renderer.info.render.frame,x:Boxing.world.actors[1].body.position.x})')
    guest.bring_to_front()
    for i in range(8):
        guest.wait_for_function("i=>Boxing.state.special.challenge.targets[i].opens_at*1000<=Date.now()",arg=i)
        guest.locator('.boxing-aim-target:visible').click(timeout=1200)
        guest.wait_for_function('i=>Boxing.state.special.challenge.targets[i].hit',arg=i,timeout=1200)
    for p in pages:p.wait_for_function("Boxing.state.special.phase==='evaded'&&!Boxing.world.timeStopped",timeout=5000)
    assert guest.evaluate('Boxing.state.players.every(p=>p.hp===50)')
    assert host.evaluate('Boxing.state.players[0].special_ready_at')==deadline
    guest.locator('.boxing-arena').screenshot(path=str(out/'aim-evaded.png'))
    # Other player activates X; no clicks -> cutscene, exactly half MAX HP.
    for p in pages:p.evaluate("window.specialStages=new Set();const tick=()=>{if(Boxing.world?.special?.active)specialStages.add(Boxing.world.special.stage);requestAnimationFrame(tick)};tick()")
    guest.locator('.cage-canvas').click();guest.keyboard.press('x')
    for p in pages:p.wait_for_function("Boxing.state.special?.phase==='aim'&&Boxing.state.special.attacker===Boxing.state.players[1].uid")
    host.locator('.boxing-arena').screenshot(path=str(out/'aim-defender.png'))
    guest.locator('.boxing-arena').screenshot(path=str(out/'aim-attacker.png'))
    host.set_viewport_size({'width':390,'height':950})
    host.locator('.boxing-arena').screenshot(path=str(out/'aim-mobile.png'))
    assert host.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    for p in pages:p.wait_for_function("Boxing.state.special.phase==='cinematic'&&Boxing.world.special.active",timeout=15000)
    for p in pages:p.wait_for_function("Boxing.state.special.complete&&!Boxing.world.special.active",timeout=10000)
    assert host.evaluate('Boxing.state.players[0].hp===25&&Boxing.state.players[1].hp===50&&Boxing.state.players[0].armor===10')
    stages=[p.evaluate('[...specialStages]') for p in pages];print('Cinematic stages',stages,flush=True)
    assert {'thigh','shoulder','elbow'}<=set(sum(stages,[])),stages
    assert host.evaluate("Boxing.state.events.filter(e=>e.special&&e.result==='hit').length===1")
    host.locator('.boxing-arena').screenshot(path=str(out/'cooldown-resume.png'))
    # Uneven 40/180 ms delivery: both clients keep receiving state and moving.
    host.set_viewport_size({'width':1200,'height':950})
    for p in pages:p.evaluate("(()=>{const aimOriginalFetch=window.fetch;let n=0;window.fetch=async(...args)=>{const r=await aimOriginalFetch(...args);if(String(args[0]).startsWith('/social/boxing/'))await new Promise(done=>setTimeout(done,++n%2?40:180));return r}})();void 0")
    host.bring_to_front();host.locator('.cage-canvas').click();before=host.evaluate('Boxing.state.players[0].x');host.keyboard.down('s');host.wait_for_timeout(1500);host.keyboard.up('s');host.wait_for_timeout(600)
    assert abs(host.evaluate('Boxing.state.players[0].x')-before)>.2
    assert abs(host.evaluate('Boxing.state.players[0].x')-guest.evaluate('Boxing.state.players[0].x'))<.25
    for p in pages:p.locator('.boxing-back').click()
    assert not errors,errors
    print('PASS two-player X: freeze, grayscale, native 8-target evade, no damage, 180s cooldown, failure cinematic, half-max HP, mobile and clean exit')
    b.close()
