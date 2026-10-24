"""Server-earned v26 game currencies; isolated from historical gold/challenge purple."""
import json,time,uuid
import membership
RATES={'beginner':1000,'pro':100,'expert':10}
CURRENCIES=(*RATES,'universal')

def schema(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS training_sets(
      set_id TEXT PRIMARY KEY REFERENCES workout_sets(id),profile_id INTEGER NOT NULL REFERENCES profiles(id),
      difficulty TEXT NOT NULL CHECK(difficulty IN ('beginner','pro','expert')),
      reps INTEGER NOT NULL CHECK(reps>=0));
      CREATE TABLE IF NOT EXISTS training_ledger(
      id TEXT PRIMARY KEY,profile_id INTEGER NOT NULL REFERENCES profiles(id),
      currency TEXT NOT NULL CHECK(currency IN ('beginner','pro','expert','universal')),
      amount INTEGER NOT NULL,kind TEXT NOT NULL,created REAL NOT NULL);
      CREATE TABLE IF NOT EXISTS training_operations(
      id TEXT PRIMARY KEY,owner TEXT NOT NULL,profile_id INTEGER NOT NULL,signature TEXT NOT NULL);
    ''')

def balance(db,profile):
    wallet=dict.fromkeys(CURRENCIES,0)
    for r in db.execute('SELECT currency,SUM(amount) amount FROM training_ledger WHERE profile_id=? GROUP BY currency',(profile,)):
        wallet[r['currency']]=r['amount']
    return wallet

def credit_db(db,set_id,profile,difficulty):
    """Called in the same transaction as the server-owned workout insert."""
    if difficulty not in RATES:raise ValueError('Invalid difficulty')
    row=db.execute('SELECT reps FROM workout_sets WHERE id=? AND profile_id=?',(set_id,profile)).fetchone()
    if not row or row['reps']<=0:return
    old=db.execute('SELECT difficulty,profile_id FROM training_sets WHERE set_id=?',(set_id,)).fetchone()
    if old and (old['difficulty']!=difficulty or old['profile_id']!=profile):raise ValueError('Set difficulty cannot change')
    db.execute('INSERT OR IGNORE INTO training_sets VALUES(?,?,?,?)',(set_id,profile,difficulty,row['reps']))
    db.execute('INSERT OR IGNORE INTO training_ledger VALUES(?,?,?,?,?,?)',('set:'+set_id,profile,difficulty,row['reps'],'workout',time.time()))

def credit(store,set_id,profile,difficulty):
    with store.lock,store.connect() as db:
        schema(db);db.execute('BEGIN IMMEDIATE')
        credit_db(db,set_id,profile,difficulty)


def overview(store,owner,profile):
    with store.lock,store.connect() as db:
        schema(db)
        return dict(wallet=balance(db,profile),rates=RATES,cost=100,vip=membership.active(store,owner),
          history=[dict(r) for r in db.execute('SELECT currency,amount,kind,created FROM training_ledger WHERE profile_id=? ORDER BY created DESC,id DESC LIMIT 30',(profile,))])

def act(store,owner,profile,data):
    import shop
    if not isinstance(data,dict):raise ValueError('Invalid request')
    key=shop.operation_id(data.get('request_id'));action=data.get('action');quantity=data.get('quantity',1)
    if type(quantity) is not int or not 1<=quantity<=100:raise ValueError('Quantity must be 1–100 / จำนวนต้องเป็น 1–100')
    currency=data.get('currency')
    if action=='exchange':
        if not isinstance(currency,str) or currency not in RATES:raise ValueError('Choose beginner, pro or expert / เลือกชนิดเหรียญ')
        payload=dict(action=action,currency=currency,quantity=quantity)
    elif action=='redeem':
        if quantity!=1:raise ValueError('One reward per request')
        payload=dict(action=action,quantity=1)
        for field,limit in [('name',100),('phone',30),('address',1000)]:
            value=data.get(field)
            if not isinstance(value,str) or not value.strip() or len(value)>limit:raise ValueError('Complete recipient details / กรอกข้อมูลผู้รับให้ครบ')
            payload[field]=value.strip()
    else:raise ValueError('Unknown action / คำสั่งไม่ถูกต้อง')
    signature=json.dumps(payload,sort_keys=True,ensure_ascii=False)
    with store.lock,store.connect() as db:
        shop.schema(db);schema(db);db.execute('BEGIN IMMEDIATE')
        if not owner.startswith('account:') or not db.execute('SELECT 1 FROM profile_owners WHERE profile_id=? AND owner=?',(profile,owner)).fetchone():
            raise PermissionError('Sign in with the owning account / เข้าสู่บัญชีเจ้าของโปรไฟล์')
        old=db.execute('SELECT * FROM training_operations WHERE id=?',(key,)).fetchone()
        if old:
            if old['owner']!=owner or old['profile_id']!=profile or old['signature']!=signature:raise ValueError('Request ID already used')
        else:
            if db.execute('SELECT 1 FROM shop_operations WHERE id=?',(key,)).fetchone():raise ValueError('Request ID already used')
        if not old:
            wallet=balance(db,profile)
            if action=='exchange':
                cost=RATES[currency]*quantity
                if wallet[currency]<cost:raise ValueError('Not enough coins / เหรียญไม่พอ')
                moves=[(currency,-cost),('universal',quantity)]
            else:
                if not membership.active_db(db,owner):raise PermissionError('VIP Home required for whey / แลกเวย์เฉพาะ VIP Home')
                if wallet['universal']<100:raise ValueError('Need 100 universal coins / ต้องมีเหรียญสากล 100 เหรียญ')
                moves=[('universal',-100)]
                db.execute('INSERT INTO shop_orders(id,owner,profile_id,status,name,phone,address,created,charge_currency,charge_amount) VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (key,owner,profile,'pending',payload['name'],payload['phone'],payload['address'],time.time(),'universal',100))
            db.execute('INSERT INTO training_operations VALUES(?,?,?,?)',(key,owner,profile,signature))
            for currency,amount in moves:db.execute('INSERT INTO training_ledger VALUES(?,?,?,?,?,?)',(key+':'+currency,profile,currency,amount,action,time.time()))

    return overview(store,owner,profile)
