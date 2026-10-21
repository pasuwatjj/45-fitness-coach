"""Atomic currency exchange and private, manually fulfilled reward requests."""
import re
import time
import uuid
import membership
import challenges
import rewards


def schema(db):
    challenges.schema(db);rewards.schema(db);membership.schema(db)
    db.executescript('''CREATE TABLE IF NOT EXISTS shop_operations(
      id TEXT PRIMARY KEY,owner TEXT NOT NULL,profile_id INTEGER NOT NULL,
      kind TEXT NOT NULL,quantity INTEGER NOT NULL,created REAL NOT NULL);
      CREATE TABLE IF NOT EXISTS currency_moves(
      id TEXT PRIMARY KEY,profile_id INTEGER NOT NULL,currency TEXT NOT NULL,
      amount INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS shop_orders(
      id TEXT PRIMARY KEY,owner TEXT NOT NULL,profile_id INTEGER NOT NULL,
      status TEXT NOT NULL,name TEXT NOT NULL,phone TEXT NOT NULL,address TEXT NOT NULL,
      created REAL NOT NULL);''')


def balance_db(db,profile):
    gold=db.execute('SELECT COALESCE(SUM(amount),0) FROM reward_ledger WHERE profile_id=?',(profile,)).fetchone()[0]
    purple=db.execute('SELECT COALESCE(SUM(amount),0) FROM purple_coins WHERE profile_id=?',(profile,)).fetchone()[0]
    for row in db.execute('SELECT currency,SUM(amount) AS total FROM currency_moves WHERE profile_id=? GROUP BY currency',(profile,)):
        if row['currency']=='gold':gold+=row['total']
        if row['currency']=='purple':purple+=row['total']
    return dict(gold=gold,purple=purple)


def overview(store,owner,profile):
    with store.lock,store.connect() as db:
        schema(db)
        balance=balance_db(db,profile)
        orders=[dict(row) for row in db.execute('SELECT id,status,created FROM shop_orders WHERE owner=? AND profile_id=? ORDER BY created DESC LIMIT 30',(owner,profile))]
    return dict(**balance,orders=orders,product='Banvit Godzilla Absolute Zero',cost=50,rate=10)


def operation_id(value):
    try:return str(uuid.UUID(value))
    except (ValueError,TypeError,AttributeError):raise ValueError('Invalid request ID')


def act(store,owner,profile,data):
    if not isinstance(data,dict):raise ValueError('Invalid request')
    key=operation_id(data.get('request_id'));kind=data.get('action')
    if kind not in ('convert','redeem'):raise ValueError('Unknown shop action')
    quantity=data.get('quantity',1)
    if type(quantity) is not int or not 1<=quantity<=100 or kind=='redeem' and quantity!=1:
        raise ValueError('Invalid quantity')
    contact={}
    if kind=='redeem':
        for field,limit in [('name',100),('phone',30),('address',1000)]:
            val=data.get(field)
            if not isinstance(val,str) or not val.strip() or len(val)>limit:raise ValueError('Complete recipient name, phone and address')
            contact[field]=val.strip()
    with store.lock,store.connect() as db:
        schema(db);db.execute('BEGIN IMMEDIATE')
        if not membership.active_db(db,owner):raise PermissionError('VIP Home required')
        old=db.execute('SELECT * FROM shop_operations WHERE id=?',(key,)).fetchone()
        if old:
            if old['owner']!=owner or old['profile_id']!=profile or old['kind']!=kind or old['quantity']!=quantity:
                raise ValueError('Request ID already used')
        else:
            wallet=balance_db(db,profile)
            if kind=='convert' and wallet['gold']<10*quantity:raise ValueError('Not enough gold coins')
            if kind=='redeem' and wallet['purple']<50:raise ValueError('Not enough purple coins')
            db.execute('INSERT INTO shop_operations VALUES(?,?,?,?,?,?)',(key,owner,profile,kind,quantity,time.time()))
            if kind=='convert':
                db.execute('INSERT INTO currency_moves VALUES(?,?,?,?)',(key+':gold',profile,'gold',-10*quantity))
                db.execute('INSERT INTO currency_moves VALUES(?,?,?,?)',(key+':purple',profile,'purple',quantity))
            else:
                db.execute('INSERT INTO currency_moves VALUES(?,?,?,?)',(key+':reserve',profile,'purple',-50))
                db.execute('INSERT INTO shop_orders VALUES(?,?,?,?,?,?,?,?)',(key,owner,profile,'pending',contact['name'],contact['phone'],contact['address'],time.time()))
    return overview(store,owner,profile)


def resolve(store,order_id,result,owner=None):
    if result not in ('cancelled','fulfilled'):raise ValueError('Invalid order status')
    with store.lock,store.connect() as db:
        schema(db);db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM shop_orders WHERE id=?',(order_id,)).fetchone()
        if not row or owner and row['owner']!=owner:raise ValueError('Order not found')
        if owner and result!='cancelled':raise PermissionError('Only administrator can fulfill orders')
        if row['status']==result:return
        if row['status']!='pending':raise ValueError('Order already resolved')
        if result=='cancelled':db.execute('INSERT INTO currency_moves VALUES(?,?,?,50)',(order_id+':refund',row['profile_id'],'purple'))
        db.execute('UPDATE shop_orders SET status=? WHERE id=?',(result,order_id))
