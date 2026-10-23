"""Email/password accounts with hashed passwords and revocable browser cookies."""
import hashlib
import re
import secrets
import sqlite3
import time
from werkzeug.security import check_password_hash, generate_password_hash

COOKIE = 'fitness_login_v7'
LIFETIME = 30 * 86400


def digest(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def schema(store):
    with store.lock, store.connect() as db:
        db.executescript('''CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS account_logins (
            token_hash TEXT PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id),
            expires REAL NOT NULL);
        ''')


def credentials(data):
    if not isinstance(data,dict):
        raise ValueError('กรอกอีเมลและรหัสผ่าน')
    email,password=data.get('email'),data.get('password')
    if not isinstance(email,str) or len(email)>254:
        raise ValueError('กรอกอีเมลให้ถูกต้อง')
    email=email.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):
        raise ValueError('กรอกอีเมลให้ถูกต้อง')
    if not isinstance(password,str) or not 8<=len(password)<=128:
        raise ValueError('รหัสผ่านต้องมี 8–128 ตัวอักษร')
    return email,password


def register(store,data):
    email,password=credentials(data)
    hashed=generate_password_hash(password)
    schema(store)
    with store.lock,store.connect() as db:
        if db.execute('SELECT 1 FROM accounts WHERE email=?',(email,)).fetchone():
            raise ValueError('อีเมลนี้สมัครแล้ว ลองเข้าสู่ระบบ')
        try:
            row=db.execute('INSERT INTO accounts(email,password_hash) VALUES(?,?)',(email,hashed))
        except sqlite3.IntegrityError as error:
            raise ValueError('อีเมลนี้สมัครแล้ว ลองเข้าสู่ระบบ') from error
        return dict(id=row.lastrowid,email=email,owner='account:'+str(row.lastrowid))


def login(store,data):
    email,password=credentials(data)
    schema(store)
    with store.lock,store.connect() as db:
        row=db.execute('SELECT * FROM accounts WHERE email=?',(email,)).fetchone()
    # Same expensive check for unknown emails limits account-enumeration timing.
    candidate=row['password_hash'] if row else DUMMY_HASH
    valid=check_password_hash(candidate,password)
    if not row or not valid:
        raise ValueError('อีเมลหรือรหัสผ่านไม่ถูกต้อง')
    return dict(id=row['id'],email=row['email'],owner='account:'+str(row['id']))


def issue(store,account):
    token=secrets.token_urlsafe(32)
    with store.lock,store.connect() as db:
        db.execute('DELETE FROM account_logins WHERE expires<?',(time.time(),))
        db.execute('INSERT INTO account_logins(token_hash,account_id,expires) VALUES(?,?,?)',
                   (digest(token),account['id'],time.time()+LIFETIME))
    return token


def lookup(store,token):
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):
        return None
    schema(store)
    with store.lock,store.connect() as db:
        row=db.execute('''SELECT a.id,a.email FROM account_logins l JOIN accounts a ON a.id=l.account_id
            WHERE l.token_hash=? AND l.expires>?''',(digest(token),time.time())).fetchone()
        return dict(id=row['id'],email=row['email'],owner='account:'+str(row['id'])) if row else None


def revoke(store,token):
    schema(store)
    with store.lock,store.connect() as db:
        db.execute('DELETE FROM account_logins WHERE token_hash=?',(digest(token),))


DUMMY_HASH=generate_password_hash('unused-account-password')
