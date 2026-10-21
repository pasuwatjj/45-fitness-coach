"""VIP entitlement, SlipOK verification and private receipt-email outbox.

No client-provided VIP flag or image alone can activate membership.
"""
import hashlib
import io
import json
import os
import re
import smtplib
import ssl
import threading
import time
import uuid
import warnings
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage

import requests
from PIL import Image, ImageOps

PRICE=50
DAYS=30
BANK_ACCOUNT='0000000000'
RECEIPT_TO='receipts@example.com'
LOCKED={'supported_row','lying_triceps','incline_press','front_raise','split_squat'}
_verify_lock=threading.Lock()
_mail_lock=threading.Lock()


def schema(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS vip_memberships(
      owner TEXT PRIMARY KEY, expires REAL NOT NULL);
      CREATE TABLE IF NOT EXISTS vip_receipts(
      id TEXT PRIMARY KEY,owner TEXT NOT NULL,email TEXT NOT NULL,
      image_hash TEXT NOT NULL UNIQUE,image BLOB NOT NULL,status TEXT NOT NULL,
      trans_key TEXT UNIQUE,created REAL NOT NULL,result TEXT NOT NULL DEFAULT '',
      mail_status TEXT NOT NULL DEFAULT 'queued',mail_attempts INTEGER NOT NULL DEFAULT 0,
      mail_after REAL NOT NULL DEFAULT 0,verify_attempts INTEGER NOT NULL DEFAULT 1,
      last_check REAL NOT NULL DEFAULT 0);
      CREATE INDEX IF NOT EXISTS vip_owner_created ON vip_receipts(owner,created);''')
    columns={r[1] for r in db.execute('PRAGMA table_info(vip_receipts)')}
    for column,definition in [('verify_attempts','INTEGER NOT NULL DEFAULT 1'),('last_check','REAL NOT NULL DEFAULT 0')]:
        if column not in columns:db.execute('ALTER TABLE vip_receipts ADD COLUMN '+column+' '+definition)


def mail_ready():
    return all(os.environ.get(k,'').strip() for k in
               ('FITNESS_SMTP_HOST','FITNESS_SMTP_USER','FITNESS_SMTP_PASSWORD'))


def payment_ready():
    return (bool(re.fullmatch(r'[0-9]+',os.environ.get('FITNESS_SLIPOK_BRANCH','')))
            and bool(os.environ.get('FITNESS_SLIPOK_KEY'))
            and os.environ.get('FITNESS_RECEIVER_CONFIRMED')==BANK_ACCOUNT and mail_ready()
            and os.environ.get('FITNESS_SERVICES_OK')=='1')


def active_db(db,owner,now=None):
    row=db.execute('SELECT expires FROM vip_memberships WHERE owner=?',(owner,)).fetchone()
    return bool(row and row['expires']>(time.time() if now is None else now))


def active(store,owner):
    with store.lock,store.connect() as db:
        schema(db)
        return active_db(db,owner)


def status(store,owner):
    with store.lock,store.connect() as db:
        schema(db)
        row=db.execute('SELECT expires FROM vip_memberships WHERE owner=?',(owner,)).fetchone()
        receipts=[dict(r) for r in db.execute('''SELECT id,status,created,result,mail_status
          FROM vip_receipts WHERE owner=? ORDER BY created DESC LIMIT 10''',(owner,))]
    expires=row['expires'] if row else None
    return dict(active=bool(expires and expires>time.time()),expires=expires,
                price=PRICE,days=DAYS,payment_ready=payment_ready(),mail_ready=mail_ready(),receipts=receipts,
                locked_exercises=sorted(LOCKED))


def normalize_image(raw):
    if not raw or len(raw)>5*1024*1024:raise ValueError('Use JPG/PNG/WebP under 5 MB')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in ('JPEG','PNG','WEBP') or source.width*source.height>16_000_000:
                    raise ValueError('Unsupported image or over 16 megapixels')
                source.load()
                picture=ImageOps.exif_transpose(source).convert('RGB')
                out=io.BytesIO();picture.save(out,'JPEG',quality=95)
                result=out.getvalue()
                if len(result)>8*1024*1024:raise ValueError('Image too large after processing')
                return result
    except (OSError,Image.DecompressionBombWarning,Image.DecompressionBombError) as exc:
        raise ValueError('Cannot read receipt image') from exc


def verify_slip(image):
    """Only a 200 success from the fixed provider with log=true is accepted."""
    response=requests.post('https://api.slipok.com/api/line/apikey/'+os.environ['FITNESS_SLIPOK_BRANCH'],
        headers={'x-authorization':os.environ['FITNESS_SLIPOK_KEY']},
        files={'files':('receipt.jpg',image,'image/jpeg')},data={'log':'true','amount':str(PRICE)},
        timeout=(8,30),allow_redirects=False)
    data=response.json()
    if response.status_code!=200 or data.get('success') is not True:
        code=str(data.get('code','unavailable'))[:20]
        # A duplicate response can contain success-looking data; never approve it.
        raise ValueError('SlipOK rejected or delayed this receipt (code '+code+'). Contact the administrator if already paid.')
    return validate_result(data)


def validate_result(data,now=None):
    d=data.get('data')
    if data.get('success') is not True or not isinstance(d,dict) or d.get('success') is not True:
        raise ValueError('Receipt not verified')
    try:amount=Decimal(str(d.get('amount')))
    except InvalidOperation:raise ValueError('Invalid amount')
    if amount!=Decimal(PRICE) or d.get('countryCode')!='TH' or str(d.get('paidLocalCurrency') or '764')!='764':
        raise ValueError('Amount must be exactly 50 THB')
    if d.get('receivingBank')!='004':raise ValueError('Receiver bank mismatch')
    masked=re.sub(r'[-\s]','',str((d.get('receiver') or {}).get('account',{}).get('value',''))).lower()
    if (len(masked)!=len(BANK_ACCOUNT) or sum(c.isdigit() for c in masked)<4
        or any(c not in 'x*0123456789' for c in masked)
        or any(c.isdigit() and c!=b for c,b in zip(masked,BANK_ACCOUNT))):
        raise ValueError('Receiver account unclear or mismatched; administrator review required')
    try:
        paid=datetime.strptime(d['transDate']+' '+d['transTime'],'%Y%m%d %H:%M:%S').replace(tzinfo=timezone(timedelta(hours=7))).timestamp()
    except (KeyError,ValueError,TypeError):raise ValueError('Cannot verify payment time')
    current=time.time() if now is None else now
    if not current-86400<=paid<=current+300:raise ValueError('Use a receipt paid within the last 24 hours')
    ref=str(d.get('transRef',''));bank=str(d.get('sendingBank',''))
    if not re.fullmatch(r'[A-Za-z0-9_-]{5,80}',ref) or not re.fullmatch(r'\d{3}',bank):
        raise ValueError('Missing transaction reference')
    return bank+':'+ref


def submit(store,owner,email,raw):
    if not payment_ready():raise ValueError('Payment verification/email is not configured. Do not transfer yet.')
    picture=normalize_image(raw);digest=hashlib.sha256(picture).hexdigest()
    # Bound provider calls; do not hold the workout database lock over HTTP.
    if not _verify_lock.acquire(blocking=False):raise ValueError('Receipt service busy. Please retry shortly.')
    try:
        with store.lock,store.connect() as db:
            schema(db)
            old=db.execute('SELECT * FROM vip_receipts WHERE image_hash=?',(digest,)).fetchone()
            if old:
                if old['owner']!=owner:raise ValueError('This receipt has already been submitted')
                if old['status'] in ('verified','checking'):return status(store,owner)
                if time.time()-old['last_check']<60:raise ValueError('Wait at least 60 seconds before rechecking')
                if old['verify_attempts']>=5:raise ValueError('Receipt recheck limit reached. Contact administrator; do not pay again.')
                receipt=old['id']
                db.execute("UPDATE vip_receipts SET status='checking',last_check=?,verify_attempts=verify_attempts+1,mail_status='waiting' WHERE id=?",(time.time(),receipt))
            else:
                recent=db.execute('SELECT COUNT(*) FROM vip_receipts WHERE owner=? AND created>?',(owner,time.time()-3600)).fetchone()[0]
                if recent>=5:raise ValueError('Maximum 5 receipts per hour. Contact the administrator.')
                receipt=str(uuid.uuid4())
                db.execute('INSERT INTO vip_receipts(id,owner,email,image_hash,image,status,created,mail_status,last_check) VALUES(?,?,?,?,?,?,?,?,?)',
                           (receipt,owner,email,digest,picture,'checking',time.time(),'waiting',time.time()))
        try:
            transaction=verify_slip(picture)
            with store.lock,store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if db.execute('SELECT 1 FROM vip_receipts WHERE trans_key=?',(transaction,)).fetchone():
                    raise ValueError('Transaction already used')
                old=db.execute('SELECT expires FROM vip_memberships WHERE owner=?',(owner,)).fetchone()
                expires=max(time.time(),old['expires'] if old else 0)+DAYS*86400
                db.execute('INSERT INTO vip_memberships(owner,expires) VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET expires=excluded.expires',(owner,expires))
                db.execute("UPDATE vip_receipts SET status='verified',trans_key=?,result='Verified: VIP activated for 30 days',mail_status='queued' WHERE id=?",(transaction,receipt))
        except Exception as error:
            message=str(error)[:220] if isinstance(error,ValueError) else 'Verification unavailable. No VIP granted; contact administrator before paying again.'
            with store.lock,store.connect() as db:
                db.execute("UPDATE vip_receipts SET status='review',result=?,mail_status='queued' WHERE id=?",(message,receipt))
        return status(store,owner)
    finally:_verify_lock.release()


def submit_manual(store,owner,email,raw):
    """Queue for human bank-statement review. Uploading never grants VIP."""
    picture=normalize_image(raw);digest=hashlib.sha256(picture).hexdigest()
    with store.lock,store.connect() as db:
        schema(db)
        old=db.execute('SELECT owner FROM vip_receipts WHERE image_hash=?',(digest,)).fetchone()
        if old and old['owner']!=owner:raise ValueError('This receipt has already been submitted')
        if not old:
            recent=db.execute('SELECT COUNT(*) FROM vip_receipts WHERE owner=? AND created>?',(owner,time.time()-3600)).fetchone()[0]
            if recent>=5:raise ValueError('Maximum 5 receipts per hour')
            db.execute('INSERT INTO vip_receipts(id,owner,email,image_hash,image,status,created,result,mail_status,last_check) VALUES(?,?,?,?,?,?,?,?,?,?)',
                (str(uuid.uuid4()),owner,email,digest,picture,'review',time.time(),'Waiting for administrator to confirm the actual bank transfer; no VIP granted.','queued',time.time()))
    return status(store,owner)

def approve_manual(store,receipt,transaction,amount,receiver):
    """LOCAL operator only, after checking the actual receiving-bank ledger."""
    if amount!=50 or receiver!=BANK_ACCOUNT or not re.fullmatch(r'[0-9]{3}:[A-Za-z0-9_-]{5,80}',transaction or ''):
        raise ValueError('Confirm 50 THB, receiver 0000000000 and BANKCODE:TRANSACTION_REF from the bank')
    with store.lock,store.connect() as db:
        schema(db);db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM vip_receipts WHERE id=?',(receipt,)).fetchone()
        if not row:raise ValueError('Receipt not found')
        if row['status']=='verified':return
        if row['status']!='review':raise ValueError('Receipt is not awaiting review')
        if db.execute('SELECT 1 FROM vip_receipts WHERE trans_key=?',(transaction,)).fetchone():raise ValueError('Transaction already used')
        old=db.execute('SELECT expires FROM vip_memberships WHERE owner=?',(row['owner'],)).fetchone()
        expires=max(time.time(),old['expires'] if old else 0)+DAYS*86400
        db.execute('INSERT INTO vip_memberships VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET expires=excluded.expires',(row['owner'],expires))
        db.execute("UPDATE vip_receipts SET status='verified',trans_key=?,result='Administrator confirmed bank transfer: VIP activated for 30 days',mail_status='queued',mail_after=0,mail_attempts=0 WHERE id=?",(transaction,receipt))

def send_pending(store):
    """Durable retries; SMTP failure does not revoke a verified membership."""
    if not mail_ready() or not _mail_lock.acquire(blocking=False):return
    try:
        with store.lock,store.connect() as db:
            schema(db)
            row=db.execute("SELECT * FROM vip_receipts WHERE mail_status='queued' AND mail_after<=? ORDER BY created LIMIT 1",(time.time(),)).fetchone()
        if not row:return
        message=EmailMessage();message['From']=os.environ['FITNESS_SMTP_USER'];message['To']=RECEIPT_TO
        message['Subject']='45 Fitness Coach VIP receipt '+row['id']
        message['Message-ID']='<45fitness-'+row['id']+'@fitness.local>'
        message.set_content('Account: '+row['email']+'\nReceipt: '+row['id']+'\nStatus: '+row['status']+'\n'+row['result'])
        message.add_attachment(row['image'],maintype='image',subtype='jpeg',filename='vip-receipt.jpg')
        success=False
        try:
            host=os.environ['FITNESS_SMTP_HOST'];port=int(os.environ.get('FITNESS_SMTP_PORT','587'));context=ssl.create_default_context()
            connection=smtplib.SMTP_SSL(host,port,timeout=12,context=context) if port==465 else smtplib.SMTP(host,port,timeout=12)
            with connection as smtp:
                if port!=465:smtp.starttls(context=context)
                smtp.login(os.environ['FITNESS_SMTP_USER'],os.environ['FITNESS_SMTP_PASSWORD']);smtp.send_message(message)
            success=True
        except Exception:pass
        attempt=row['mail_attempts']+1
        with store.lock,store.connect() as db:
            db.execute('UPDATE vip_receipts SET mail_status=?,mail_attempts=?,mail_after=? WHERE id=?',
                       ('sent' if success else 'failed' if attempt>=6 else 'queued',attempt,time.time()+min(1800,30*2**attempt),row['id']))
    finally:_mail_lock.release()


def run_mail_worker(store):
    while True:
        try:
            with store.lock,store.connect() as db:
                schema(db)
                db.execute("UPDATE vip_receipts SET status='review',result='Verification interrupted. Administrator review required; do not pay again.',mail_status='queued' WHERE status='checking' AND created<?",(time.time()-300,))
            send_pending(store)
        except Exception:pass
        time.sleep(15)
