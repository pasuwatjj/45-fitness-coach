"""Local persistent profiles/sets. Scores come from server counters, not client input."""
import json
import hashlib
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import threading
from planner import PlannerMixin, SCHEMA


class LeaderboardStore(PlannerMixin):
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS workout_sets (
                id TEXT PRIMARY KEY, profile_id INTEGER NOT NULL REFERENCES profiles(id),
                exercise TEXT NOT NULL, arm_mode TEXT NOT NULL,
                reps INTEGER NOT NULL CHECK(reps > 0), flagged INTEGER NOT NULL,
                left_reps INTEGER NOT NULL, right_reps INTEGER NOT NULL,
                observations TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS health_records (
                id TEXT PRIMARY KEY, profile_id INTEGER NOT NULL REFERENCES profiles(id),
                measured_on TEXT NOT NULL, inputs TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE INDEX IF NOT EXISTS health_profile_date ON health_records(profile_id,measured_on);
        ''')
        db.executescript(SCHEMA)
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create_profile(self, name):
        if not isinstance(name, str):
            raise ValueError('กรุณาใส่ชื่อผู้เล่น')
        name = ' '.join(name.split())
        if not name or len(name) > 30 or not name.isprintable():
            raise ValueError('ชื่อผู้เล่นต้องยาว 1–30 ตัวอักษร')
        with self.lock, self.connect() as db:
            db.execute('INSERT OR IGNORE INTO profiles(name) VALUES(?)', (name,))
            row = db.execute('SELECT id,name FROM profiles WHERE name=? COLLATE NOCASE', (name,)).fetchone()
            return dict(row)

    def profiles(self):
        with self.lock, self.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,name FROM profiles ORDER BY name COLLATE NOCASE')]

    def profile(self, profile_id):
        with self.lock, self.connect() as db:
            row = db.execute('SELECT id,name FROM profiles WHERE id=?', (profile_id,)).fetchone()
            return dict(row) if row else None

    def save_set(self, set_id, profile_id, exercise, arm_mode, reps, flagged, left, right, observations, plan=None, difficulty=None):
        if reps <= 0:
            return False
        with self.lock, self.connect() as db:
            if difficulty is not None:
                from training_economy import schema, credit_db
                schema(db)
            db.execute('BEGIN IMMEDIATE')
            result = db.execute('''INSERT OR IGNORE INTO workout_sets
                (id,profile_id,exercise,arm_mode,reps,flagged,left_reps,right_reps,observations)
                VALUES(?,?,?,?,?,?,?,?,?)''', (set_id,profile_id,exercise,arm_mode,reps,flagged,left,right,
                                              json.dumps(observations,ensure_ascii=False)))
            if difficulty is not None:credit_db(db,set_id,profile_id,difficulty)
            if plan is not None:
                credited = self.credit_plan(db,set_id,profile_id,exercise,arm_mode,reps,plan)
                return dict(saved=True,credited=credited)
            return result.rowcount == 1

    def standings(self, exercise='curl', arm_mode='both'):
        with self.lock, self.connect() as db:
            rows = [dict(r) for r in db.execute('''SELECT p.id AS profile_id,p.name,
                    SUM(s.reps) AS total,MAX(s.reps) AS best_set,COUNT(*) AS sets
                FROM workout_sets s JOIN profiles p ON p.id=s.profile_id
                WHERE s.exercise=? AND s.arm_mode=? GROUP BY p.id
                ORDER BY total DESC,best_set DESC,p.name COLLATE NOCASE''', (exercise,arm_mode))]
        last_score, rank = None, 0
        for index, row in enumerate(rows, 1):
            if row['total'] != last_score:
                rank = index
            row['rank'] = rank
            last_score = row['total']
        return rows

    def save_health(self, profile_id, data):
        from health import analyze
        analysis = analyze(data)
        inputs = analysis['inputs']
        payload = json.dumps(inputs, sort_keys=True, ensure_ascii=False)
        record_id = hashlib.sha256((str(profile_id) + ':' + payload).encode('utf-8')).hexdigest()
        with self.lock, self.connect() as db:
            if not db.execute('SELECT id FROM profiles WHERE id=?', (profile_id,)).fetchone():
                raise ValueError('ไม่พบชื่อผู้เล่น')
            result = db.execute('''INSERT OR IGNORE INTO health_records
                (id,profile_id,measured_on,inputs) VALUES(?,?,?,?)''',
                (record_id,profile_id,inputs['measured_on'],payload))
            saved = db.execute('SELECT created_at FROM health_records WHERE id=?', (record_id,)).fetchone()
        return dict(id=record_id,analysis=analysis,created_at=saved['created_at'],new_record=result.rowcount==1)

    def health_history(self, profile_id):
        from health import analyze
        with self.lock, self.connect() as db:
            rows = db.execute('''SELECT id,inputs,created_at FROM health_records
                WHERE profile_id=? ORDER BY measured_on DESC,created_at DESC,id DESC LIMIT 30''',
                (profile_id,)).fetchall()
        return [dict(id=r['id'],analysis=analyze(json.loads(r['inputs'])),created_at=r['created_at']) for r in rows]

    def streak_standings(self):
        from planner import streaks,today_thailand
        today=today_thailand()
        result=[]
        with self.lock,self.connect() as db:
            for p in db.execute('SELECT id,name FROM profiles').fetchall():
                dates=db.execute('SELECT day FROM workout_days WHERE profile_id=? AND day<=? ORDER BY day',(p['id'],today.isoformat())).fetchall()
                days=[self._day(db,p['id'],d['day'],today) for d in dates]
                score=streaks(days,today)
                if score['completed']:
                    result.append(dict(profile_id=p['id'],name=p['name'],**{k:score[k] for k in ('current','best','completed')}))
        result.sort(key=lambda r:(-r['current'],-r['best'],-r['completed'],r['name'].casefold()))
        previous=None;rank=0
        for i,row in enumerate(result,1):
            if row['current']!=previous:rank=i
            row['rank']=rank;previous=row['current']
        return result
