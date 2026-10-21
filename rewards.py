"""Private, transactional digital rewards. No real goods or monetary value."""
from planner import today_thailand

CATALOG=[dict(id='spark',cost=30,icon='✨',th='ประกายแรก',en='First spark'),
         dict(id='steady',cost=80,icon='🔥',th='ใจสม่ำเสมอ',en='Steady spirit'),
         dict(id='star',cost=150,icon='🌟',th='ดาวแห่งความตั้งใจ',en='Dedication star')]

def schema(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS quality_sets(
        id TEXT PRIMARY KEY,profile_id INTEGER NOT NULL REFERENCES profiles(id),exercise TEXT NOT NULL,
        arm_mode TEXT NOT NULL,reps INTEGER NOT NULL,accepted INTEGER NOT NULL DEFAULT 0,rejected INTEGER NOT NULL,unverified INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS reward_ledger(
        id TEXT PRIMARY KEY,profile_id INTEGER NOT NULL REFERENCES profiles(id),amount INTEGER NOT NULL,
        kind TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS reward_unlocks(
        profile_id INTEGER NOT NULL REFERENCES profiles(id),item TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(profile_id,item));''')

    if 'accepted' not in {r[1] for r in db.execute('PRAGMA table_info(quality_sets)')}:
        db.execute('ALTER TABLE quality_sets ADD COLUMN accepted INTEGER NOT NULL DEFAULT 0')

def save_quality(store,set_id,profile,exercise,arm,reps,rejected,unverified,accepted=None):
    if not (reps or rejected or unverified or accepted):return
    with store.lock,store.connect() as db:
        schema(db);db.execute('BEGIN IMMEDIATE')
        recorded=db.execute('SELECT reps FROM workout_sets WHERE id=? AND profile_id=?',(set_id,profile)).fetchone()
        valid=recorded['reps'] if recorded else 0
        db.execute('INSERT OR IGNORE INTO quality_sets(id,profile_id,exercise,arm_mode,reps,rejected,unverified,accepted) VALUES(?,?,?,?,?,?,?,?)',
                   (set_id,profile,exercise,arm,valid,rejected,unverified,accepted if accepted is not None else valid*(2 if arm=='both' else 1)))
        if valid:db.execute('INSERT OR IGNORE INTO reward_ledger(id,profile_id,amount,kind) VALUES(?,?,?,?)',('set:'+set_id,profile,valid,'workout'))

def completed_days(store,db,profile):
    today=today_thailand()
    dates=db.execute('SELECT day FROM workout_days WHERE profile_id=? AND day<=? ORDER BY day',(profile,today.isoformat())).fetchall()
    return [d['day'] for d in dates if store._day(db,profile,d['day'],today)['complete'] and store._day(db,profile,d['day'],today)['items']]

def overview(store,profile):
    with store.lock,store.connect() as db:
        schema(db)
        coins=db.execute('SELECT COALESCE(SUM(amount),0) FROM reward_ledger WHERE profile_id=?',(profile,)).fetchone()[0]
        unlocked=[r['item'] for r in db.execute('SELECT item FROM reward_unlocks WHERE profile_id=?',(profile,))]
        claimed={r['id'] for r in db.execute("SELECT id FROM reward_ledger WHERE profile_id=? AND kind='fire'",(profile,))}
        available=sum(f'day:{profile}:{day}' not in claimed for day in completed_days(store,db,profile))
        history=[dict(r) for r in db.execute('SELECT amount,kind,created_at FROM reward_ledger WHERE profile_id=? ORDER BY created_at DESC,id DESC LIMIT 20',(profile,))]
    from challenges import overview as challenge_overview
    purple=challenge_overview(store,profile)['purple_coins']
    fire=store.plan_month(profile,today_thailand().strftime('%Y-%m'))['streak']
    return dict(coins=coins,purple_coins=purple,fire=fire,redemption_open=False,available_fire=available,fire_rate=10,items=CATALOG,unlocked=unlocked,history=history)

def claim_fire(store,profile):
    with store.lock,store.connect() as db:
        schema(db);db.execute('BEGIN IMMEDIATE')
        for day in completed_days(store,db,profile):
            db.execute('INSERT OR IGNORE INTO reward_ledger(id,profile_id,amount,kind) VALUES(?,?,10,?)',(f'day:{profile}:{day}',profile,'fire'))
    return overview(store,profile)

def redeem(store,profile,item):
    product=next((p for p in CATALOG if p['id']==item),None)
    if not product:raise ValueError('Unknown reward')
    with store.lock,store.connect() as db:
        schema(db);db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM reward_unlocks WHERE profile_id=? AND item=?',(profile,item)).fetchone():
            coins=db.execute('SELECT COALESCE(SUM(amount),0) FROM reward_ledger WHERE profile_id=?',(profile,)).fetchone()[0]
            if coins<product['cost']:raise ValueError('Not enough coins')
            db.execute('INSERT INTO reward_unlocks(profile_id,item) VALUES(?,?)',(profile,item))
            db.execute('INSERT INTO reward_ledger(id,profile_id,amount,kind) VALUES(?,?,?,?)',(f'redeem:{profile}:{item}',profile,-product['cost'],'redeem'))
    return overview(store,profile)
