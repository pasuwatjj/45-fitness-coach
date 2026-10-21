"""Hashed recovery numbers, persistent attempt limits and one-use reset tickets."""
import re
import secrets
import time
from werkzeug.security import generate_password_hash, check_password_hash
import accounts

def schema(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS recovery_numbers(
      account_id INTEGER PRIMARY KEY, number_hash TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS recovery_limits(key TEXT PRIMARY KEY, attempts INTEGER, until REAL);
      CREATE TABLE IF NOT EXISTS recovery_tickets(token_hash TEXT PRIMARY KEY, account_id INTEGER,
      expires REAL NOT NULL);''')

def number(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{2,3}',value):
        raise ValueError('ใช้เลขที่ชอบ 2–3 หลัก / Use 2–3 digits')
    return value

def save(store,account_id,value):
    hashed=generate_password_hash(number(value))
    with store.lock,store.connect() as db:
        schema(db)
        db.execute('INSERT INTO recovery_numbers VALUES(?,?) ON CONFLICT(account_id) DO UPDATE SET number_hash=excluded.number_hash',(account_id,hashed))
        db.execute('DELETE FROM recovery_tickets WHERE account_id=?',(account_id,))

def has_number(store,account_id):
    with store.lock,store.connect() as db:
        schema(db)
        return bool(db.execute('SELECT 1 FROM recovery_numbers WHERE account_id=?',(account_id,)).fetchone())

def verify(store,email,value,address):
    raise ValueError('ใช้ลิงก์ที่ส่งทางอีเมล / Use the emailed reset link')

def reset(store,ticket,password):
    _,password=accounts.credentials(dict(email='reset@example.com',password=password))
    if not isinstance(ticket,str) or len(ticket)!=43:raise ValueError('ลิงก์กู้บัญชีหมดอายุ / Recovery session expired')
    hashed=generate_password_hash(password)
    with store.lock,store.connect() as db:
        schema(db);db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT account_id FROM recovery_tickets WHERE token_hash=? AND expires>?',(accounts.digest(ticket),time.time())).fetchone()
        if not row:raise ValueError('ลิงก์กู้บัญชีหมดอายุ / Recovery session expired')
        account_id=row['account_id']
        db.execute('UPDATE accounts SET password_hash=? WHERE id=?',(hashed,account_id))
        db.execute('DELETE FROM account_logins WHERE account_id=?',(account_id,))
        db.execute('DELETE FROM recovery_tickets WHERE account_id=?',(account_id,))
    return 'account:'+str(account_id)
