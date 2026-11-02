"""Local two-account admin room: V slow motion, guest belt and consented rematch."""
import os,time,sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];dbpath=os.environ['BOXING_TEST_DB'];assert root.startswith('http://127.0.0.1:') and dbpath.startswith('/tmp/')
out=Path('work/boxing-counter-review');out.mkdir(parents=True,exist_ok=True)
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
    # Schedule real keyboard presses against both active clients at one wall time.
    for p in pages:
        p.evaluate("window.counterSeen=false;window.cueSeen=false;new MutationObserver(()=>{if(document.querySelector('.boxing-damage.counter'))counterSeen=true;if(!document.querySelector('.boxing-time-cue').hidden)cueSeen=true}).observe(document.querySelector('.boxing-arena'),{subtree:true,childList:true,attributes:true})")
    when=time.time()*1000+600
    for p in pages:
        p.evaluate("at=>setTimeout(()=>{document.body.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyQ',key:'q',bubbles:true}));setTimeout(()=>document.body.dispatchEvent(new KeyboardEvent('keyup',{code:'KeyQ',key:'q',bubbles:true})),75)},Math.max(0,at-Date.now()))",when)
    for p in pages:
        p.wait_for_function("counterSeen&&Boxing.state.events.some(e=>e.result==='counter')",timeout=6000)
        assert p.evaluate('Boxing.state.players.every(p=>p.hp===50&&p.armor===10)')
        assert p.evaluate('Boxing.state.pending_strikes.length===0')
        assert p.locator('.boxing-damage.counter').inner_text()=='Counter · 0'
        assert p.locator('.hp-bar').first.bounding_box()['height']>=23
    host.locator('.boxing-arena').screenshot(path=str(out/'counter-desktop.png'))
    host.bring_to_front();host.locator('.cage-canvas').click();host.keyboard.press('v')
    for p in pages:
        p.wait_for_function('cueSeen&&Boxing.state.time_scale===.4',timeout=5000)
        assert p.locator('.boxing-time-active').is_visible()
        assert p.locator('.boxing-time-players').inner_text().find('CD 1:')>=0 or 'CD 2:00' in p.locator('.boxing-time-players').inner_text()
        assert p.locator('.boxing-skill').is_disabled()
    assert abs(host.evaluate('Boxing.state.players[0].skill_ready_at-Boxing.state.slow_started_at')-120)<.01
    assert abs(host.evaluate('Boxing.state.slow_until-Boxing.state.slow_started_at')-60)<.01
    host.locator('.boxing-arena').screenshot(path=str(out/'time-shift-desktop.png'))
    guest.set_viewport_size({'width':390,'height':950});guest.locator('.boxing-arena').screenshot(path=str(out/'hud-mobile.png'))
    assert guest.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    for p in pages:p.wait_for_function("document.querySelector('.boxing-time-cue').hidden",timeout=4000)
    host.locator('.boxing-expand').click();host.wait_for_timeout(300)
    assert host.locator('.boxing-time-hud').is_visible()
    host.locator('.boxing-arena').screenshot(path=str(out/'hud-fullscreen.png'))
    host.locator('.boxing-expand').click()
    # Deterministic wall-time boundaries on the public presentation component.
    fixture=a.new_page();fixture.goto(root+'/45-fitness-coach?lang=en');fixture.evaluate("document.body.innerHTML='<div id=fixture style=position:relative;width:390px;height:500px></div>';window.testHUD=new BoxingSkillHUD(document.getElementById('fixture'),(th,en)=>en);window.m={id:'fixture',status:'active',slow_started_at:1000,slow_until:1060,slow_by:1,players:[{uid:1,skill_ready_at:1120},{uid:2}]};testHUD.update(m,1,1000000,'V')")
    assert 'CD 2:00' in fixture.locator('.boxing-time-hud').inner_text()
    assert fixture.locator('.boxing-time-active').inner_text()=='BOTH SLOWED · 1:00'
    fixture.evaluate("testHUD.update(m,1,1060000,'V')")
    assert fixture.locator('.boxing-time-active').is_hidden();assert 'CD 1:00' in fixture.locator('.boxing-time-hud').inner_text()
    fixture.evaluate("testHUD.update(m,1,1120000,'V')")
    assert fixture.locator('.boxing-time-player b').first.inner_text()=='READY'
    fixture.emulate_media(reduced_motion='reduce');fixture.evaluate("m.slow_started_at=1120;m.slow_until=1180;m.slow_by=2;m.players[1].skill_ready_at=1240;testHUD.update(m,1,1120000,'V')")
    assert 'OPPONENT ACTIVATED' in fixture.locator('.boxing-time-cue').inner_text()
    assert fixture.locator('.boxing-time-cue').evaluate('e=>getComputedStyle(e).animationName')=='none'
    fixture.evaluate('testHUD.reset()');assert fixture.locator('.boxing-time-cue').is_hidden();assert fixture.locator('.boxing-time-hud').is_hidden()
    for p in pages:p.locator('.boxing-back').click()
    assert not errors,errors
    print('PASS simultaneous keyboard Counter on two clients, HP/armor preserved, 60s skill/120s cooldown, both HUDs, cue cleanup, wall-time boundary, opponent activation, reduced motion, mobile/fullscreen, no JS errors')
    b.close()
