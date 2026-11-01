"""Disposable local DB only: admin room UI, guest disclosure, permissions and latency."""
import os,time,sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];dbpath=os.environ['BOXING_TEST_DB']
assert root.startswith('http://127.0.0.1:') and dbpath.startswith('/tmp/')
out=Path('work/boxing-admin-review');out.mkdir(parents=True,exist_ok=True)
def account(c,name):
    assert c.request.post(root+'/auth/register',data={'email':f'room{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'}).ok
    h={'X-Coach-Session':c.request.post(root+'/session').json()['session_token']}
    pid=c.request.post(root+'/profiles',headers=h,data={'name':name+' '+str(time.time_ns())[-6:]}).json()['profile']['id']
    assert c.request.post(root+f'/profiles/{pid}/character',headers=h,data={'appearance':{}}).ok
    return c.request.get(root+'/social/me',headers=h).json()['account_id'],pid,h
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-background-timer-throttling','--disable-renderer-backgrounding'])
    a=b.new_context(viewport={'width':1200,'height':950});g=b.new_context(viewport={'width':390,'height':950})
    uid,pid,h=account(a,'Admin room host');gid,gpid,gh=account(g,'Room guest')
    a.request.post(root+'/social/friends',headers=h,data={'action':'request','account_id':gid});g.request.post(root+'/social/friends',headers=gh,data={'action':'accept','account_id':uid})
    with sqlite3.connect(dbpath) as db:db.execute("INSERT INTO account_roles(account_id,role) VALUES(?,'admin')",(uid,))
    pages=[a.new_page(),g.new_page()];errors=[]
    for p in pages:
        p.on('pageerror',lambda e:errors.append(str(e)));p.goto(root+'/45-fitness-coach?lang=en');p.locator('#homeBoxingTile').click();p.wait_for_function("!document.querySelector('[data-mode=friends]').disabled")
        p.locator('[data-mode=friends]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-primary').click();p.wait_for_function("Boxing.mode==='friends'&&!document.querySelector('select[aria-label=\"Choose a friend\"]').hidden")
    host,guest=pages
    assert guest.locator('.boxing-custom-room').is_hidden();assert host.locator('.boxing-custom-room').is_visible()
    host.locator('#boxingCustomRoom').check();host.get_by_role('spinbutton',name='HP',exact=True).fill('120');host.get_by_role('spinbutton',name='Armor',exact=True).fill('25');host.get_by_role('spinbutton',name='All body parts Lv',exact=True).fill('6')
    host.locator('.boxing-custom-room').screenshot(path=str(out/'admin-settings.png'))
    host.get_by_role('button',name='Invite friend',exact=True).click();host.wait_for_function("Boxing.state?.status==='invited'")
    guest.get_by_role('button',name='Accept invitation',exact=True).wait_for();assert 'HP 120 / Armor 25 / Lv 6' in guest.locator('.boxing-rooms').inner_text()
    guest.locator('.boxing-rooms').screenshot(path=str(out/'guest-invitation.png'));guest.get_by_role('button',name='Accept invitation',exact=True).click()
    for p in pages:
        p.wait_for_function("Boxing.state?.status==='active'",timeout=20000);p.wait_for_function("Boxing.world?.actors.every(a=>a.body)",timeout=60000)
        assert p.evaluate('Boxing.state.players.every(p=>p.max_hp===120&&p.max_armor===25&&p.damage.left===6&&p.kick_damage===6)')
        assert p.locator('.hp-bar progress').first.evaluate('e=>e.max')==120
        assert p.locator('.armor-bar progress').first.evaluate('e=>e.max')==25
        p.evaluate("const original=Boxing.world.renderer.render.bind(Boxing.world.renderer);let last=0;Boxing.world.renderer.render=(...args)=>{if(performance.now()-last>100){last=performance.now();original(...args)}};void 0")
    # Hold responses: the local movement preview and punch still start before any reply.
    host.evaluate("window.roomFetch=window.fetch;window.roomReplies=0;window.fetch=async(...args)=>{const r=await roomFetch(...args);if(String(args[0]).includes('/social/boxing/')){await new Promise(resolve=>setTimeout(resolve,400));roomReplies++}return r};void 0")
    host.wait_for_timeout(600)
    host.bring_to_front();host.locator('.cage-canvas').click();host.evaluate("window.beforeInput=performance.now();window.beforePreview=Boxing.world.sampleStates(beforeInput,Boxing.world.states)[0].x;window.beforeReplies=roomReplies")
    host.keyboard.down('s');host.wait_for_function('Boxing.world.sampleStates(performance.now(),Boxing.world.states)[0].x<beforePreview-.015',timeout=300);host.keyboard.up('s')
    host.evaluate('window.punchInputAt=performance.now()');host.keyboard.press('q');host.wait_for_function('Boxing.world.actors[0].punchAt>punchInputAt',timeout=1000);assert host.evaluate('Boxing.world.actors[0].punchAt-punchInputAt')<200
    host.evaluate('window.fetch=window.roomFetch;void 0');host.wait_for_timeout(800)
    assert a.request.get(root+f'/social/boxing/training/{pid}',headers=h).json()['max_hp']==50
    assert g.request.get(root+f'/social/boxing/training/{gpid}',headers=gh).json()['max_hp']==50
    assert guest.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    mid=host.evaluate('Boxing.state.id');assert g.request.post(root+'/social/boxing/'+mid,headers=gh,data={'action':'heartbeat','custom_settings':{'hp':1,'armor':0,'level':100}}).status==400
    host.locator('.boxing-arena').screenshot(path=str(out/'admin-match.png'))
    host.locator('.boxing-back').click();guest.locator('.boxing-back').click()
    assert not errors,errors
    print('PASS admin-only settings, guest disclosure, custom HP/armor/levels on both fighters, mobile layout, immediate movement/punch during delayed replies, immutable settings and unchanged profile HP')
    b.close()
