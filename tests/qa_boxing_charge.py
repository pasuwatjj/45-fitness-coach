"""Two browsers exercise mouse settings, charging, stamina, effects and responsive HUD."""
import os,time,sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];dbpath=os.environ['BOXING_TEST_DB'];assert root.startswith('http://127.0.0.1:') and dbpath.startswith('/tmp/')
out=Path('work/boxing-charge-review');out.mkdir(parents=True,exist_ok=True)
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
        if p == pages[0]:
            p.locator('[data-mode=settings]').click()
            p.locator('[data-binding=punchLeft]').click();p.locator('.fighter-dialog h2').click()
            p.locator('[data-binding=punchRight]').click();p.locator('.fighter-dialog h2').click(button='right')
            assert p.evaluate("BoxingKeys.bindings.punchLeft==='Mouse0'&&BoxingKeys.bindings.punchRight==='Mouse2'")
            p.keyboard.press('Escape')
        p.locator('[data-mode=friends]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-primary').click();p.get_by_role('button',name='Return to match',exact=True).click()
    host,guest=pages
    for p in pages:
        p.wait_for_function("Boxing.state?.status==='active'",timeout=20000);p.wait_for_function('Boxing.world?.actors.every(a=>a.body)',timeout=60000)
        p.evaluate("const original=Boxing.world.renderer.render.bind(Boxing.world.renderer);let last=0;Boxing.world.renderer.render=(...args)=>{if(performance.now()-last>100){last=performance.now();original(...args)}};void 0")
    assert host.locator('.boxing-key-row').count()==13
    assert host.locator('.boxing-key-row[data-action=dash]').count()==1
    assert host.locator('.boxing-key-row[data-action=forward]').count()==0
    assert 'LMB' in host.locator('[data-action=punchLeft]').inner_text()
    assert 'RMB' in host.locator('[data-action=punchRight]').inner_text()
    host.locator('.boxing-hints-toggle').click();assert host.locator('.boxing-key-list').is_hidden()
    assert host.evaluate("localStorage.getItem('45-boxing-key-hints')")=='off'
    host.locator('.boxing-hints-toggle').click();assert host.locator('.boxing-key-list').is_visible()
    host.evaluate("window.hitSeen=false;const hit=Boxing.world.hitEffect.bind(Boxing.world);Boxing.world.hitEffect=(...a)=>{hitSeen=true;hit(...a)};void 0")
    canvas=host.locator('.cage-canvas');box=canvas.bounding_box();host.mouse.move(box['x']+box['width']*.4,box['y']+box['height']*.5)
    yaw=host.evaluate('Boxing.world.yaw');host.mouse.down(button='right');host.wait_for_timeout(1800)
    assert host.evaluate('Boxing.state.players[1].hp')==50
    assert '2.0' in host.locator('.boxing-charge-readout').inner_text()
    assert host.evaluate('Math.abs(Boxing.world.actors[0].chest.rotation.y)>.05')
    assert host.locator('.boxing-charge-readout').is_visible()
    host.locator('.boxing-arena').screenshot(path=str(out/'charge-desktop.png'))
    # Screenshot readback can stall software WebGL beyond charge freshness; wait for a confirmed server charge again.
    host.wait_for_function("Boxing.state.players[0].charge_hand==='right'&&Boxing.state.combat_now-Boxing.state.players[0].charge_at>=1.5",timeout=8000)
    host.mouse.up(button='right')
    host.wait_for_function('Boxing.state.players[1].hp===44',timeout=6000)
    guest.wait_for_function('Boxing.state.players[1].hp===44',timeout=6000)
    assert host.evaluate('hitSeen')
    assert host.evaluate('Boxing.state.players[0].stamina<20')
    assert host.locator('.stamina-bar').count()==2
    assert host.evaluate('Boxing.state.event.charge_multiplier')==2
    host.wait_for_timeout(650)
    host.keyboard.down('w');host.wait_for_timeout(500);host.keyboard.up('w');host.wait_for_timeout(200)
    canvas.click(position={'x':box['width']*.4,'y':box['height']*.5})
    host.wait_for_function('Boxing.state.players[1].hp===41',timeout=6000)
    host.wait_for_timeout(700)
    # Guard cancels a held mouse charge without committing a punch.
    host.mouse.down(button='right');host.wait_for_timeout(700);host.keyboard.down('f');host.mouse.up(button='right');host.keyboard.up('f');host.wait_for_timeout(700)
    assert host.evaluate('Boxing.state.players[1].hp')==41
    host.set_viewport_size({'width':390,'height':950});host.wait_for_timeout(400)
    assert host.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    assert host.evaluate("document.querySelector('.boxing-key-list').getBoundingClientRect().bottom < document.querySelector('.boxing-ability-actions').getBoundingClientRect().top")
    host.locator('.boxing-arena').screenshot(path=str(out/'hints-mobile.png'))
    host.locator('.boxing-expand').click();host.wait_for_timeout(200);assert host.locator('.boxing-key-hints').is_visible()
    host.locator('.boxing-arena').screenshot(path=str(out/'hints-fullscreen.png'));host.locator('.boxing-expand').click()
    host.set_viewport_size({'width':1200,'height':950});host.emulate_media(reduced_motion='reduce')
    host.evaluate("Boxing.world.hitEffect({result:'hit'},{x:0,z:0})")
    host.wait_for_timeout(1000);assert host.evaluate('Boxing.world.hitEffects.length')==0
    for p in pages:p.locator('.boxing-back').click()
    assert not errors,errors
    print('PASS real mouse setting capture, charge ×2 synchronized to both players, normal tap, guard cancel, hit effects, compact live bindings without movement, toggle persistence, mobile/fullscreen and reduced motion')
    b.close()
