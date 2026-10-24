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
    columns={r[1] for r in db.execute('PRAGMA table_info(shop_orders)')}
    if 'charge_currency' not in columns:db.execute("ALTER TABLE shop_orders ADD COLUMN charge_currency TEXT NOT NULL DEFAULT 'purple'")
    if 'charge_amount' not in columns:db.execute('ALTER TABLE shop_orders ADD COLUMN charge_amount INTEGER NOT NULL DEFAULT 50')


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
        orders=[dict(row) for row in db.execute('SELECT id,status,created,charge_currency,charge_amount FROM shop_orders WHERE owner=? AND profile_id=? ORDER BY created DESC LIMIT 30',(owner,profile))]
    from training_economy import overview as training_overview
    return dict(**balance,orders=orders,product='Banvit Godzilla Absolute Zero',legacy=True,**training_overview(store,owner,profile))


def operation_id(value):
    try:return str(uuid.UUID(value))
    except (ValueError,TypeError,AttributeError):raise ValueError('Invalid request ID')


def act(store,owner,profile,data):
    from training_economy import act as training_act
    training_act(store,owner,profile,data)
    return overview(store,owner,profile)


def resolve(store,order_id,result,owner=None):
    if result not in ('cancelled','fulfilled'):raise ValueError('Invalid order status')
    with store.lock,store.connect() as db:
        schema(db)
        from training_economy import schema as training_schema
        training_schema(db);db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM shop_orders WHERE id=?',(order_id,)).fetchone()
        if not row or owner and row['owner']!=owner:raise ValueError('Order not found')
        if owner and result!='cancelled':raise PermissionError('Only administrator can fulfill orders')
        if row['status']==result:return
        if row['status']!='pending':raise ValueError('Order already resolved')
        if result=='cancelled':
            if row['charge_currency']=='universal':
                db.execute('INSERT INTO training_ledger VALUES(?,?,?,?,?,?)',(order_id+':refund',row['profile_id'],'universal',row['charge_amount'],'refund',time.time()))
            else:db.execute('INSERT INTO currency_moves VALUES(?,?,?,?)',(order_id+':refund',row['profile_id'],row['charge_currency'],row['charge_amount']))
        db.execute('UPDATE shop_orders SET status=? WHERE id=?',(result,order_id))
