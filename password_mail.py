"""Email-only password recovery; short favorite numbers never authenticate a reset."""
import logging
import os
import re
import secrets
import smtplib
import ssl
import time
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage
from threading import BoundedSemaphore
from urllib.parse import urlsplit
import accounts
import recovery

_pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='password-mail')
_slots=BoundedSemaphore(8)

def smtp_ready():
    return all(os.environ.get(k) for k in ('FITNESS_SMTP_HOST','FITNESS_SMTP_USER','FITNESS_SMTP_PASSWORD'))

def deliver(email,link):
    message=EmailMessage()
    message['From']=os.environ['FITNESS_SMTP_USER'];message['To']=email
    message['Subject']='45 Fitness Coach — Reset your password'
    message.set_content('ตั้งรหัสผ่านใหม่ / Reset your password\n\n'+link+'\n\nลิงก์ใช้ได้ครั้งเดียว ภายใน 15 นาที หากไม่ได้ขอ ให้ละเว้นอีเมลนี้\nOne use, expires in 15 minutes. Ignore this email if you did not request it.')
    port=int(os.environ.get('FITNESS_SMTP_PORT','587'));context=ssl.create_default_context()
    connection=smtplib.SMTP_SSL(os.environ['FITNESS_SMTP_HOST'],port,timeout=12,context=context) if port==465 else smtplib.SMTP(os.environ['FITNESS_SMTP_HOST'],port,timeout=12)
    with connection as smtp:
        if port!=465:smtp.starttls(context=context)
        smtp.login(os.environ['FITNESS_SMTP_USER'],os.environ['FITNESS_SMTP_PASSWORD']);smtp.send_message(message)

def issue_and_send(store,email,base):
    token=None
    try:
        with store.lock,store.connect() as db:
            recovery.schema(db)
            row=db.execute('SELECT id,email FROM accounts WHERE email=? COLLATE NOCASE',(email,)).fetchone()
            if not row:return
            token=secrets.token_urlsafe(32)
            # Multiple requested links can coexist until one succeeds; sending failures do not invalidate an earlier link.
            db.execute('INSERT INTO recovery_tickets VALUES(?,?,?)',(accounts.digest(token),row['id'],time.time()+900))
        deliver(row['email'],base+'#reset='+token)
    except Exception:
        if token:
            with store.lock,store.connect() as db:db.execute('DELETE FROM recovery_tickets WHERE token_hash=?',(accounts.digest(token),))
        logging.warning('Password reset email could not be delivered. Check SMTP configuration. No credentials or reset tokens are logged.')

def request_reset(store,email,address,base):
    if not isinstance(email,str) or len(email)>254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email.strip()):raise ValueError('กรอกอีเมลให้ถูกต้อง / Enter a valid email')
    if not smtp_ready() or not base or urlsplit(base).scheme!='https':raise ValueError('ผู้ดูแลต้องตั้งค่าอีเมล SMTP และเปิดลิงก์ HTTPS ก่อน / Administrator must configure SMTP and an HTTPS public link')
    email=email.strip().lower();now=time.time()
    with store.lock,store.connect() as db:
        recovery.schema(db)
        db.execute('DELETE FROM recovery_limits WHERE until<?',(now,));db.execute('DELETE FROM recovery_tickets WHERE expires<?',(now,))
        keys=[accounts.digest('mail:'+email),accounts.digest('mail-ip:'+str(address))]
        for key in keys:
            row=db.execute('SELECT attempts FROM recovery_limits WHERE key=?',(key,)).fetchone()
            if row and row['attempts']>=5:raise ValueError('รอ 15 นาทีแล้วลองใหม่ / Try again in 15 minutes')
        for key in keys:db.execute('INSERT INTO recovery_limits VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET attempts=attempts+1',(key,now+900))
    if not _slots.acquire(blocking=False):raise ValueError('ระบบส่งอีเมลกำลังทำงาน ลองอีกครั้งภายหลัง / Mail busy, please retry later')
    try:
        future=_pool.submit(issue_and_send,store,email,base)
        future.add_done_callback(lambda _: _slots.release())
    except Exception:
        _slots.release();raise ValueError('Mail unavailable / ส่งอีเมลไม่ได้ชั่วคราว')
