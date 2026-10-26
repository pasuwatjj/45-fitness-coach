"""Analytics-only reset: retain immutable workout/economy records and hide old charts."""
def schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS analytics_hidden(profile_id INTEGER,kind TEXT,id TEXT,PRIMARY KEY(profile_id,kind,id))')
def hidden(store,pid,kind='set'):
    with store.lock,store.connect() as db:
        schema(db)
        return {r[0] for r in db.execute('SELECT id FROM analytics_hidden WHERE profile_id=? AND kind=?',(pid,kind))}
def reset(store,pid,active=()):
    with store.lock,store.connect() as db:
        schema(db)
        db.execute('BEGIN IMMEDIATE')
        for table,kind in [('set_angles','set'),('workout_sets','set'),('quality_sets','set'),('cardio_rounds','cardio')]:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                db.execute(f'INSERT OR IGNORE INTO analytics_hidden SELECT profile_id,?,id FROM {table} WHERE profile_id=?',(kind,pid))
        db.executemany('INSERT OR IGNORE INTO analytics_hidden VALUES(?,?,?)',[(pid,kind,id) for kind,id in active])
