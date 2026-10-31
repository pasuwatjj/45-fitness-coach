"""Disposable local account/DB checks for reminders, friend unread state and UI."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import time,sqlite3,json
root='http://127.0.0.1:5055';out=Path('work/inbox-review');out.mkdir(parents=True,exist_ok=True)
def account(context):
 r=context.request.post(root+'/auth/register',data={'email':f'inbox{time.time_ns()}@example.com','password':'Testing-pass-123','recovery_number':'48'});assert r.ok,r.text()
 token=context.request.post(root+'/session').json()['session_token'];headers={'X-Coach-Session':token}
 r=context.request.post(root+'/profiles',headers=headers,data={'name':'Inbox'+str(time.time_ns())});assert r.ok,r.text()
 uid=context.request.get(root+'/social/me',headers=headers).json()['account_id'];return uid,headers
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':1050});other=b.new_context();uid,h=account(c);friend,fh=account(other)
  assert c.request.post(root+'/social/friends',headers=h,data={'action':'request','account_id':friend}).ok
  assert other.request.post(root+'/social/friends',headers=fh,data={'action':'accept','account_id':uid}).ok
  text='วันนี้เก่งมาก! <img src=x onerror="window.badChat=true">'
  assert other.request.post(root+f'/social/chat/{uid}',headers=fh,data={'body':text,'client_id':'browser-message-'+str(time.time_ns())}).ok
  page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(root+'/45-fitness-coach');page.wait_for_timeout(1200);page.evaluate("document.body.dataset.theme='power'")
  page.wait_for_function('Inbox.unread===1');assert not page.locator('#inboxTab .inbox-dot').is_hidden()
  page.locator('.home-hero').screenshot(path=str(out/f'{width}-home.png'))
  page.locator('#homeInboxTile').click();assert page.locator('.bat-particle').count()>0
  page.wait_for_selector('.reminder-settings form');page.wait_for_timeout(1000);assert page.locator('.bat-particle').count()==0
  form=page.locator('.reminder-settings form');form.locator('.reminder-all input').fill('19:30');form.locator('.reminder-all button').click();assert form.locator('[name=enabled]').is_checked()
  assert all(form.locator(f'[name=time-{i}]').input_value()=='19:30' for i in range(7))
  form.locator('[name=time-2]').fill('20:15');form.locator('[name=day-6]').uncheck()
  with page.expect_response(lambda r:r.url.endswith('/inbox/reminders') and r.request.method=='POST') as saved:form.locator('[type=submit]').click()
  assert saved.value.ok,saved.value.text();settings=saved.value.json();assert settings['days'][2]['time']=='20:15' and not settings['days'][6]['enabled']
  page.reload();page.wait_for_timeout(900);page.evaluate("setTab('inbox')");page.wait_for_selector('.reminder-settings form');assert form.locator('[name=time-2]').input_value()=='20:15';assert not form.locator('[name=day-6]').is_checked()
  # Move only this disposable account's reminder checkpoint back to verify due delivery.
  settings['days']=[{'day':i,'enabled':True,'time':'00:00'} for i in range(7)];assert c.request.post(root+'/social/inbox/reminders',headers=h,data=settings).ok
  with sqlite3.connect('work/inbox-qa.db') as db:db.execute('UPDATE workout_reminders SET effective_at=?,checked_at=? WHERE account_id=?',(time.time()-86400,time.time()-86400,uid))
  page.evaluate("setTab('home')");page.evaluate('Inbox.refresh()');page.wait_for_function('Inbox.unread===2')
  page.evaluate("setTab('inbox')");page.wait_for_selector('.system-message');page.wait_for_function('Inbox.unread===1');page.locator('#inboxPage').screenshot(path=str(out/f'{width}-inbox.png'))
  page.locator('.inbox-thread').click();page.wait_for_selector('.friend-chat[open] .chat-bubble');page.wait_for_function('Inbox.unread===0');assert page.locator('#inboxTab .inbox-dot').is_hidden();assert page.locator('.friend-chat .chat-messages').inner_text().find('<img')>=0;assert page.evaluate('window.badChat!==true')
  page.locator('.friend-chat textarea').fill('ขอบคุณ! พร้อมเล่นตามตารางแล้ว');page.locator('.friend-chat form button').click();page.wait_for_function("document.querySelectorAll('.chat-bubble.mine').length===1")
  page.locator('.friend-chat').evaluate('d=>d.close()');assert c.request.get(root+'/social/inbox',headers=h).json()['unread']==0
  assert other.request.post(root+f'/social/chat/{uid}',headers=fh,data={'body':'ข้อความใหม่อีกครั้ง','client_id':'browser-next-'+str(time.time_ns())}).ok
  page.evaluate("setTab('home')");page.evaluate('Inbox.refresh()');page.wait_for_function('Inbox.unread===1');page.reload();page.wait_for_function('window.Inbox?.unread===1')
  # The custom coin selector still controls the original value and respects running locks.
  page.evaluate("setTab('workout')");page.locator('.difficulty-trigger').click();page.wait_for_selector('#difficultyOptions');assert page.locator('#difficultyOptions .coin-art').count()==3
  page.locator('.difficulty-picker').screenshot(path=str(out/f'{width}-difficulty-trigger.png'))
  page.locator('#difficultyOptions [data-value=expert]').click();assert page.locator('#trainingDifficulty').input_value()=='expert'
  page.locator('.difficulty-trigger').press('ArrowDown');page.keyboard.press('ArrowUp');page.keyboard.press('Enter');assert page.locator('#trainingDifficulty').input_value()=='pro'
  page.evaluate("window.uiState={...fitnessState,running:true,difficulty:'expert'};Object.defineProperty(window,'fitnessState',{get:()=>uiState,set:()=>{},configurable:true})");page.wait_for_function("document.querySelector('.difficulty-trigger').disabled");assert page.locator('#trainingDifficulty').input_value()=='expert'
  page.evaluate('uiState.running=false');page.wait_for_function("!document.querySelector('.difficulty-trigger').disabled")
  page.emulate_media(reduced_motion='reduce');page.evaluate("setTab('home')");page.locator('#homeInboxTile').click();assert page.locator('.bat-particle').count()==0
  for name in ['rewards','calendar','profile','health','friends']:
   page.evaluate('(name)=>setTab(name)',name);page.wait_for_timeout(400);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'),name
   if name in ['rewards','calendar']:page.locator('#'+name+'Page').screenshot(path=str(out/f'{width}-{name}.png'))
  assert not errors,errors;c.close();other.close();print(width,'PASS weekly/all-days settings, persistence, due messages, private friend chat, unread/read/new/reload, coin picker/keyboard/lock, bats/reduced motion, page overflow',flush=True)
 b.close()
