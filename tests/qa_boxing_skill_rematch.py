"""Local two-account admin room: V slow motion, guest belt and consented rematch."""
import os,time,sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];dbpath=os.environ['BOXING_TEST_DB'];assert root.startswith('http://127.0.0.1:') and dbpath.startswith('/tmp/')
out=Path('work/boxing-skill-review');out.mkdir(parents=True,exist_ok=True)
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
    m=a.request.post(root+'/social/boxing/invite',headers=h,data={'profile':pid,'friend':gid,'control_mode':'computer','custom_settings':{'hp':6,'armor':10,'level':3}}).json();mid=m['id'];assert g.request.post(root+'/social/boxing/'+mid,headers=gh,data={'action':'accept','profile':gpid}).ok
    pages=[a.new_page(),g.new_page()];errors=[]
    for p in pages:
        p.on('pageerror',lambda e:errors.append(str(e)));p.goto(root+'/45-fitness-coach?lang=en');p.locator('#homeBoxingTile').click();p.wait_for_function("!document.querySelector('[data-mode=friends]').disabled")
        p.locator('[data-mode=friends]').click();p.locator('[data-control=computer]').click();p.locator('.fighter-primary').click();p.get_by_role('button',name='Return to match',exact=True).click()
    host,guest=pages
    for p in pages:
        p.wait_for_function("Boxing.state?.status==='active'",timeout=20000);p.wait_for_function('Boxing.world?.actors.every(a=>a.body)',timeout=60000)
        p.evaluate("const original=Boxing.world.renderer.render.bind(Boxing.world.renderer);let last=0;Boxing.world.renderer.render=(...args)=>{if(performance.now()-last>100){last=performance.now();original(...args)}};void 0")
    host.bring_to_front();host.locator('.cage-canvas').click();host.keyboard.press('v')
    for p in pages:p.wait_for_function("Boxing.state.time_scale===.4&&BoxingMotion.speed===.4",timeout=5000)
    deadline=host.evaluate('Boxing.state.slow_until');assert host.locator('.boxing-skill').is_disabled();assert guest.locator('.boxing-skill').is_disabled()
    host.keyboard.press('v');assert host.evaluate('Boxing.state.slow_until')==deadline
    for p in pages:
        p.evaluate('window.clockProbe={real:performance.now(),game:BoxingMotion.now()}');p.wait_for_timeout(650)
        ratio=p.evaluate('(BoxingMotion.now()-clockProbe.game)/(performance.now()-clockProbe.real)');assert .38<ratio<.42,ratio
    guest.bring_to_front();guest.locator('.cage-canvas').click();guest.keyboard.press('q');guest.wait_for_function('Boxing.state.players[0].hp===3',timeout=8000)
    guest.locator('.boxing-arena').screenshot(path=str(out/'slow-motion.png'))
    guest.wait_for_timeout(1200);guest.keyboard.press('e');guest.wait_for_function("Boxing.state.status==='round_break'",timeout=8000)
    guest.wait_for_function("Boxing.state.status==='active'&&Boxing.state.round===2",timeout=20000)
    guest.keyboard.press('q');guest.wait_for_function('Boxing.state.players[0].hp===3',timeout=8000);guest.wait_for_timeout(1200);guest.keyboard.press('e')
    for p in pages:p.wait_for_function("Boxing.state.status==='finished'&&Boxing.state.belt_awarded",timeout=20000)
    assert guest.evaluate('Boxing.state.winner')==gid
    assert g.request.get(root+f'/social/boxing/belts/{gpid}',headers=gh).json()['belts']==1
    assert g.request.get(root+f'/social/boxing/belts/{gpid}',headers=gh).json()['belts']==1
    guest.locator('.boxing-result').screenshot(path=str(out/'guest-belt-rematch.png'))
    guest.get_by_role('button',name='Play again with friend',exact=True).click();guest.get_by_role('button',name='Waiting for friend · Cancel',exact=True).click();guest.get_by_role('button',name='Play again with friend',exact=True).click()
    host.get_by_role('button',name='Friend wants a rematch · Accept',exact=True).click()
    for p in pages:
        p.wait_for_function("id=>Boxing.state.id!==id&&Boxing.state.status==='active'",arg=mid,timeout=20000)
        assert p.evaluate('Boxing.state.players.every(p=>p.hp===6&&p.armor===10&&p.wins===0)&&Boxing.state.custom_settings.level===3')
        assert p.evaluate('BoxingMotion.speed===1');assert p.locator('.boxing-skill').is_enabled()
    assert host.evaluate('Boxing.state.id')==guest.evaluate('Boxing.state.id')
    assert g.request.get(root+f'/social/boxing/belts/{gpid}',headers=gh).json()['belts']==1
    host.locator('.boxing-arena').screenshot(path=str(out/'rematch.png'))
    host.locator('.boxing-back').click();guest.locator('.boxing-back').click();assert not errors,errors
    print('PASS V slow motion on both clients, shared 40% animation clock, cooldown/no stacking, guest custom-room win awards exactly one belt, cancel/accept rematch without invitations, shared new ID and reset HP/armor/scores/skill')
    b.close()
