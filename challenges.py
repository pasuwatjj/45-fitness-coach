"""Server-earned purple coins; explicit repeatable 20-curl challenge, no orders."""
import uuid
TARGET=20

def schema(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS challenge_runs(
      id TEXT PRIMARY KEY,profile_id INTEGER NOT NULL REFERENCES profiles(id),
      progress INTEGER NOT NULL DEFAULT 0,complete INTEGER NOT NULL DEFAULT 0,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE UNIQUE INDEX IF NOT EXISTS one_active_challenge ON challenge_runs(profile_id) WHERE complete=0;
      CREATE TABLE IF NOT EXISTS challenge_credits(
      set_id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES challenge_runs(id),reps INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS purple_coins(
      run_id TEXT PRIMARY KEY REFERENCES challenge_runs(id),profile_id INTEGER NOT NULL REFERENCES profiles(id),
      amount INTEGER NOT NULL CHECK(amount=1),created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS currency_moves(
      id TEXT PRIMARY KEY,profile_id INTEGER NOT NULL,currency TEXT NOT NULL,amount INTEGER NOT NULL);''')

def active_id(store,profile):
    with store.lock,store.connect() as db:
        schema(db)
        r=db.execute('SELECT id FROM challenge_runs WHERE profile_id=? AND complete=0',(profile,)).fetchone()
        return r['id'] if r else None

def overview(store,profile):
    with store.lock,store.connect() as db:
        schema(db)
        row=db.execute('SELECT * FROM challenge_runs WHERE profile_id=? ORDER BY complete ASC,created_at DESC,rowid DESC LIMIT 1',(profile,)).fetchone()
        coins=db.execute('SELECT COALESCE(SUM(amount),0) FROM purple_coins WHERE profile_id=?',(profile,)).fetchone()[0]
        coins+=db.execute("SELECT COALESCE(SUM(amount),0) FROM currency_moves WHERE profile_id=? AND currency='purple'",(profile,)).fetchone()[0]
    return dict(target=TARGET,exercise='curl',purple_coins=coins,run=dict(row) if row else None)

def begin(store,profile):
    with store.lock,store.connect() as db:
        schema(db);db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM challenge_runs WHERE profile_id=? AND complete=0',(profile,)).fetchone():
            db.execute('INSERT INTO challenge_runs(id,profile_id) VALUES(?,?)',(str(uuid.uuid4()),profile))
    return overview(store,profile)

def credit(store,run_id,set_id,profile):
    if not run_id:return
    with store.lock,store.connect() as db:
        schema(db);db.execute('BEGIN IMMEDIATE')
        run=db.execute('SELECT * FROM challenge_runs WHERE id=? AND profile_id=? AND complete=0',(run_id,profile)).fetchone()
        saved=db.execute("SELECT reps FROM workout_sets WHERE id=? AND profile_id=? AND exercise='curl'",(set_id,profile)).fetchone()
        if not run or not saved:return
        result=db.execute('INSERT OR IGNORE INTO challenge_credits(set_id,run_id,reps) VALUES(?,?,?)',(set_id,run_id,saved['reps']))
        if not result.rowcount:return
        progress=min(TARGET,run['progress']+saved['reps']);complete=int(progress>=TARGET)
        db.execute('UPDATE challenge_runs SET progress=?,complete=? WHERE id=?',(progress,complete,run_id))
        if complete:db.execute('INSERT OR IGNORE INTO purple_coins(run_id,profile_id,amount) VALUES(?,?,1)',(run_id,profile))
