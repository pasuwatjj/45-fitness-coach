"""V44 tracked exercise energy; standard MET estimates, never rep-derived calories."""
from datetime import datetime, timezone, timedelta, date
import math, time, uuid
TH = timezone(timedelta(hours=7))
METHOD = 'met-active-v1'
# Adult Compendium 2024. Conservative general/moderate choices, not game difficulty.
def activity(kind, exercise):
    if kind == 'cardio':
        return (3.8, '02022') if exercise == 'pushup' else (3.5, '02030') if exercise == 'upper' else (7.5, '02020')
    return 3.5, '02054'

def schema(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS activity_energy_v44(
    segment_id TEXT NOT NULL, profile_id INTEGER NOT NULL, day TEXT NOT NULL,
    kind TEXT NOT NULL, exercise TEXT NOT NULL, seconds REAL NOT NULL,
    weight_kg REAL, met REAL NOT NULL, met_code TEXT NOT NULL, gross_kcal REAL,
    active_kcal REAL, method TEXT NOT NULL,
    PRIMARY KEY(segment_id,day));
    CREATE INDEX IF NOT EXISTS energy_v44_profile_day ON activity_energy_v44(profile_id,day);
    CREATE TRIGGER IF NOT EXISTS energy_v44_profile_deleted AFTER DELETE ON profiles
    BEGIN DELETE FROM activity_energy_v44 WHERE profile_id=OLD.id; END;''')

def kcal(met, weight, seconds):
    if weight is None:return None, None
    return met*3.5*weight/200*seconds/60, max(0,met-1)*3.5*weight/200*seconds/60

class ActivityMeter:
    """Only server-timed intervals with consecutive visible moving poses are counted.
    A 1s gap drops the interval. Two-person mode never enters this meter.
    SQLite receives absolute totals so retries are idempotent.
    """
    def __init__(self, store):
        self.store=store; self.key=None; self.rows={}; self.previous=None
        self.last=None; self.last_write=0; self.weight=None; self.segment=None
    def tick(self, profile, set_id, kind, exercise, poses, enabled=True, now=None, wall=None):
        now=time.monotonic() if now is None else now
        wall=time.time() if wall is None else wall
        key=(profile,set_id,kind,exercise)
        if key!=self.key:
            self.flush(); self.key=key; self.rows={}; self.segment=str(uuid.uuid4())
            self.previous=None; self.last=None; self.last_write=now
            from character import dimensions
            value=dimensions(self.store,profile).get('weight_kg') if profile else None
            self.weight=float(value) if isinstance(value,(float,int)) and not isinstance(value,bool) and math.isfinite(value) and 5<=value<=350 else None
        points={}
        if poses and enabled:
            for i in (11,12,13,14,15,16,23,24,25,26,27,28):
                p=poses[i] if len(poses)>i else None
                if p is not None and (getattr(p,'visibility',0) or 0)>=.5 and all(math.isfinite(v) for v in (p.x,p.y)):
                    points[i]=(p.x,p.y)
        dt=now-self.last if self.last is not None else 0
        common=points.keys() & (self.previous or {}).keys()
        moving=False
        if enabled and 0<dt<=1 and len(common)>=4:
            # Require limb motion relative to shoulders, rejecting camera/body translation.
            if all(i in common for i in (11,12)):
                cx=sum(points[i][0]-self.previous[i][0] for i in (11,12))/2
                cy=sum(points[i][1]-self.previous[i][1] for i in (11,12))/2
                speeds=[math.hypot(points[i][0]-self.previous[i][0]-cx,points[i][1]-self.previous[i][1]-cy)/dt for i in common if i not in (11,12)]
                moving=sum(.018<v<3 for v in speeds)>=2
        if moving and profile:
            # Split at local midnight; never assign a whole session to its finish date.
            start=wall-dt
            while start<wall:
                local=datetime.fromtimestamp(start,TH)
                midnight=datetime.combine(local.date()+timedelta(days=1),datetime.min.time(),TH).timestamp()
                end=min(wall,midnight); day=local.date().isoformat()
                self.rows[day]=self.rows.get(day,0)+(end-start); start=end
        self.previous=points if enabled else None; self.last=now if enabled else None
        if now-self.last_write>=10:
            self.last_write=now; self.flush()
    def flush(self):
        if not self.rows or self.key is None:return
        profile,_,kind,exercise=self.key; met,code=activity(kind,exercise)
        with self.store.lock,self.store.connect() as db:
            schema(db)
            for day,seconds in self.rows.items():
                gross,active=kcal(met,self.weight,seconds)
                db.execute('''INSERT INTO activity_energy_v44 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(segment_id,day) DO UPDATE SET seconds=excluded.seconds,
                gross_kcal=excluded.gross_kcal,active_kcal=excluded.active_kcal''',
                (self.segment,profile,day,kind,exercise,seconds,self.weight,met,code,gross,active,METHOD))
    def pause(self):
        try:self.flush()
        finally:self.last=None;self.previous=None

def summary(store,profile,day=None):
    selected=date.fromisoformat(day) if day else datetime.now(TH).date()
    if selected>datetime.now(TH).date():raise ValueError('เลือกวันนี้หรือวันที่ผ่านมา / Choose today or an earlier date')
    with store.lock,store.connect() as db:
        schema(db)
        rows=[dict(r) for r in db.execute('''SELECT kind,exercise,met,met_code,weight_kg,
        SUM(seconds) seconds,SUM(gross_kcal) gross_kcal,SUM(active_kcal) active_kcal
        FROM activity_energy_v44 WHERE profile_id=? AND day=?
        GROUP BY kind,exercise,met,met_code,weight_kg ORDER BY kind,exercise''',(profile,selected.isoformat()))]
    return dict(day=selected.isoformat(),timezone='Asia/Bangkok',method=METHOD,rows=rows,
        gross_kcal=round(sum(r['gross_kcal'] or 0 for r in rows),1),
        active_kcal=round(sum(r['active_kcal'] or 0 for r in rows),1),
        tracked_seconds=round(sum(r['seconds'] for r in rows),1),
        missing_weight_seconds=round(sum(r['seconds'] for r in rows if r['weight_kg'] is None),1))
