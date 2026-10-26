"""Server-authoritative jumping-jack rounds. Coordinates are camera estimates, not clinical scores."""
import math
import time
import uuid


def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS cardio_rounds(
        id TEXT PRIMARY KEY,profile_id INTEGER NOT NULL REFERENCES profiles(id),
        mode TEXT NOT NULL,reps INTEGER NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

    columns={r[1] for r in db.execute('PRAGMA table_info(cardio_rounds)')}
    for name,kind in [('duration','REAL DEFAULT 15'),('kind',"TEXT DEFAULT 'ranked'"),('active_seconds','REAL'),('weight_kg','REAL'),('met','REAL'),('kcal','REAL'),('effort','TEXT'),('tolerance','INTEGER DEFAULT 10')]:
        if name not in columns:db.execute(f'ALTER TABLE cardio_rounds ADD COLUMN {name} {kind}')


def options(data):
    tolerance=data.get('tolerance',10)
    if type(tolerance) is not int or not 5<=tolerance<=50:raise ValueError('Tolerance must be 5–50 degrees / เผื่อองศา 5–50 องศา')
    kind=data.get('kind','ranked');duration=data.get('duration',15)
    if kind not in ('ranked','timed'):raise ValueError('Select ranked or timed mode / เลือกโหมดให้ถูกต้อง')
    if type(duration) is not int or not 15<=duration<=1800:raise ValueError('Duration must be 15–1800 seconds / เวลา 15–1800 วินาที')
    if kind=='ranked' and duration!=15:raise ValueError('Ranked rounds are 15 seconds / รอบจัดอันดับ 15 วินาที')
    weight=data.get('weight_kg')
    if weight in ('',None):weight=None
    else:
        if isinstance(weight,bool):raise ValueError('Invalid weight / น้ำหนักไม่ถูกต้อง')
        try:weight=float(weight)
        except (TypeError,ValueError):raise ValueError('Invalid weight / น้ำหนักไม่ถูกต้อง')
        if not math.isfinite(weight) or not 20<=weight<=350:raise ValueError('Weight must be 20–350 kg / น้ำหนัก 20–350 กก.')
    effort=data.get('effort','moderate')
    if effort not in ('moderate','vigorous'):raise ValueError('Invalid effort / ระดับความหนักไม่ถูกต้อง')
    return dict(duration=duration,kind=kind,weight_kg=weight,effort=effort,tolerance=tolerance)


def history(store,pid):
    with store.lock,store.connect() as db:
        schema(db)
        return [dict(r) for r in db.execute('SELECT *, date(created_at, "+7 hours") day FROM cardio_rounds WHERE profile_id=? ORDER BY created_at DESC,id DESC LIMIT 500',(pid,))]


class JumpingJackRound:
    duration=15.0
    def __init__(self,store,profile_id,mode,clock=time.monotonic,*,duration=15,kind="ranked",weight_kg=None,effort="moderate",tolerance=10):
        self.store,self.profile_id,self.mode,self.clock=store,profile_id,mode,clock
        self.duration,self.kind,self.weight_kg,self.effort=duration,kind,weight_kg,effort
        self.met=(7.5 if effort=='vigorous' else 3.8) if mode=='full' and weight_kg is not None else None
        self.tolerance=tolerance;self.source=None
        self.active_seconds=0.;self.motion_at=None;self.motion_points=None
        self.id=str(uuid.uuid4());self.start_at=None;self.reps=0;self.phase='ready'
        self.last_frame=None;self.last_rep=-100;self.candidate=None;self.since=0
        self.saved=False;self.cancelled=False;self.cue='ready';self.armed=False

    def _finish(self,now):
        if self.cancelled or self.saved or self.start_at is None or now<self.start_at+self.duration:return
        from rewards import schema as reward_schema
        with self.store.lock,self.store.connect() as db:
            schema(db);reward_schema(db);db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR IGNORE INTO cardio_rounds(id,profile_id,mode,reps,duration,kind,active_seconds,weight_kg,met,kcal,effort,tolerance) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       (self.id,self.profile_id,self.mode,self.reps,self.duration,self.kind,round(self.active_seconds,2),self.weight_kg,self.met,self.calories(),self.effort,self.tolerance))
            if self.reps:db.execute('INSERT OR IGNORE INTO reward_ledger(id,profile_id,amount,kind) VALUES(?,?,?,?)',
                                  ('cardio:'+self.id,self.profile_id,self.reps,'cardio'))
        self.saved=True;self.cue='done'

    def calories(self):
        # Gross energy during observed movement, not measured metabolism.
        return round(self.met*3.5*self.weight_kg/200*(self.active_seconds/60),2) if self.met is not None else None

    def stop(self):
        self._finish(self.clock())
        if not self.saved:self.cancelled=True;self.cue='cancelled'

    def snapshot(self):
        now=self.clock();self._finish(now)
        return dict(id=self.id,mode=self.mode,reps=self.reps,phase=self.phase,cue=self.cue,
                    duration=self.duration,kind=self.kind,tolerance=self.tolerance,angle_source=self.source,active_seconds=round(self.active_seconds,2),kcal=self.calories(),weight_kg=self.weight_kg,met=self.met,effort=self.effort,
                    preparing=max(0,math.ceil(self.start_at-now)) if self.start_at else None,
                    remaining=round(max(0,min(self.duration,self.start_at+self.duration-now)),2) if self.start_at else self.duration,
                    done=self.saved,cancelled=self.cancelled,coins=self.reps if self.saved else 0)

    def update(self,points,aspect=1,world=None):
        now=self.clock();self._finish(now)
        if self.saved or self.cancelled:return self.snapshot()
        if self.last_frame is not None and now-self.last_frame>1.25:
            self.phase='ready';self.armed=False;self.candidate=None
        self.last_frame=now
        ids=[11,12,13,14,15,16,23,24]+([25,26,27,28] if self.mode=='full' else [])
        if not points or any((points[i].visibility or 0)<.55 or not -.03<=points[i].x<=1.03 or not -.03<=points[i].y<=1.03 for i in ids):
            self.motion_at=None;self.motion_points=None
            self.cue='visible';self.candidate=None;self.armed=False;self.phase='ready';return self.snapshot()
        use_world=world is not None and len(world)>max(ids) and all(all(math.isfinite(v) for v in (world[i].x,world[i].y,world[i].z)) for i in ids)
        source='estimated_3D' if use_world else '2D'
        if self.source is not None and self.source!=source:self.armed=False;self.phase='ready';self.candidate=None;self.motion_at=None;self.motion_points=None
        self.source=source
        if use_world:points=world;aspect=1
        torso=abs((points[23].y+points[24].y-points[11].y-points[12].y)/2)
        width=math.dist((points[11].x,points[11].y,points[11].z),(points[12].x,points[12].y,points[12].z)) if use_world else abs(points[11].x-points[12].x)*aspect
        if torso<.09 or width<.07:
            self.motion_at=None;self.motion_points=None
            self.cue='front';self.armed=False;self.candidate=None;return self.snapshot()
        # Count only adjacent readable frames with visible wrist/ankle motion.
        tracked=[15,16]+([27,28] if self.mode=='full' else [])
        xy=[(points[i].x*aspect,points[i].y) for i in tracked]
        if self.start_at is not None and now>=self.start_at and self.motion_at is not None and 0<now-self.motion_at<=.5:
            dt=now-self.motion_at
            speed=max(math.hypot(x-a,y-b) for (x,y),(a,b) in zip(xy,self.motion_points))/dt/torso
            if speed>.15:self.active_seconds+=max(0,now-max(self.motion_at,self.start_at))
        self.motion_at=now;self.motion_points=xy
        def angle(shoulder,elbow,hip):
            a=((elbow.x-shoulder.x)*aspect,elbow.y-shoulder.y)+((elbow.z-shoulder.z,) if use_world else ())
            b=((hip.x-shoulder.x)*aspect,hip.y-shoulder.y)+((hip.z-shoulder.z,) if use_world else ())
            den=math.hypot(*a)*math.hypot(*b)
            return math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(a,b))/den)))) if den else 0
        up=all(points[w].y<points[s].y+.05*torso and angle(points[s],points[e],points[h])>max(85,105-(self.tolerance-10)*.5) for s,e,w,h in [(11,13,15,23),(12,14,16,24)])
        down=all(points[w].y>points[s].y+.5*torso for s,w in [(11,15),(12,16)])
        if self.mode=='full':
            spread=(math.dist((points[27].x,points[27].y,points[27].z),(points[28].x,points[28].y,points[28].z)) if use_world else abs(points[27].x-points[28].x)*aspect)/width
            up=up and spread>1.15
            down=down and spread<.85
        pose='up' if up else 'down' if down else 'middle'
        if pose!=self.candidate:self.candidate=pose;self.since=now
        if now-self.since<.055:return self.snapshot()
        if self.start_at is None:
            self.start_at=now;self.phase='down' if pose=='down' else 'ready';self.armed=pose=='down';self.cue='raise' if self.armed else 'ready'
            return self.snapshot()
        if now<self.start_at:return self.snapshot()
        if not self.armed:
            if pose=='down':self.armed=True;self.phase='down'
            self.cue='ready';return self.snapshot()
        if pose=='up' and self.phase=='down':self.phase='up';self.cue='lower'
        elif pose=='down' and self.phase=='up':
            if now-self.last_rep>=.28:self.reps+=1;self.last_rep=now
            self.phase='down';self.cue='raise'
        elif pose=='down':self.cue='raise'
        return self.snapshot()


def ranking(store,mode,tolerance=10):
    with store.lock,store.connect() as db:
        schema(db)
        return [dict(r) for r in db.execute('''SELECT p.id,p.name,MAX(c.reps) best,SUM(c.reps) total,COUNT(*) rounds
            FROM cardio_rounds c JOIN profiles p ON p.id=c.profile_id WHERE c.mode=? AND c.kind='ranked' AND c.duration=15 AND COALESCE(c.tolerance,10)=?
            GROUP BY p.id ORDER BY best DESC,total DESC,p.id LIMIT 50''',(mode,tolerance))]


class PushUpRound(JumpingJackRound):
    """Side-view, full-body up/down/up counter. Thresholds are app heuristics, not clinical grading."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.met=None;self.side=None;self.cue='push_ready';self.low_angle=180;self.high_angle=0

    def update(self,points,aspect=1,world=None):
        now=self.clock();self._finish(now)
        if self.saved or self.cancelled:return self.snapshot()
        gap=self.last_frame is not None and now-self.last_frame>1.25
        self.last_frame=now
        def invalid(cue):
            self.phase='ready';self.armed=False;self.candidate=None;self.motion_at=None;self.cue=cue;self.low_angle=180;self.high_angle=0
            return self.snapshot()
        if not points or len(points)<29:return invalid('visible')
        sides=[(11,13,15,23,25,27),(12,14,16,24,26,28)]
        def visible(ids):return all(points[i].visibility>=.6 and 0<=points[i].x<=1 and 0<=points[i].y<=1 for i in ids)
        available=[ids for ids in sides if visible(ids)]
        if not available:return invalid('visible')
        ids=self.side if self.side in available else max(available,key=lambda v:min(points[i].visibility for i in v))
        if gap or self.side!=ids:invalid('push_ready')
        self.side=ids
        use_world=world is not None and len(world)>max(ids) and all(all(math.isfinite(v) for v in (world[i].x,world[i].y,world[i].z)) for i in ids)
        source='estimated_3D' if use_world else '2D'
        if self.source is not None and self.source!=source:invalid('push_ready')
        self.source=source
        s,e,w,h,k,a=[(world[i].x,world[i].y,world[i].z) if use_world else (points[i].x*aspect,points[i].y) for i in ids]
        def angle(a,b,c):
            u=tuple(x-y for x,y in zip(a,b));v=tuple(x-y for x,y in zip(c,b));den=math.hypot(*u)*math.hypot(*v)
            return math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(u,v))/den)))) if den>1e-8 else 0
        length=math.dist(s,a)
        if length<.25 or abs(s[1]-a[1])>length*.5:return invalid('push_side')
        if angle(s,h,a)<155 or angle(h,k,a)<150:return invalid('push_line')
        if w[1]<s[1]+length*.025 or math.hypot(*[w[i]-s[i] for i in range(len(s)) if i!=1])>length*.45:return invalid('push_hands')
        bend=angle(s,e,w)
        allowance=min(15,max(-2.5,(self.tolerance-10)*.5))
        pose='up' if bend>=150-allowance else 'down' if bend<=100+allowance else 'middle'
        self.low_angle=min(self.low_angle,bend);self.high_angle=max(self.high_angle,bend)
        if self.start_at is not None and now>=self.start_at and self.motion_at is not None and 0<now-self.motion_at<=.5:
            if abs(bend-self.motion_points)>2:self.active_seconds+=max(0,now-max(self.start_at,self.motion_at))
        self.motion_at=now;self.motion_points=bend
        if pose!=self.candidate:self.candidate=pose;self.since=now
        if now-self.since<.055:return self.snapshot()
        if self.start_at is None:
            self.start_at=now;self.phase='up' if pose=='up' else 'ready';self.armed=pose=='up';self.cue='push_lower' if self.armed else 'push_ready'
            return self.snapshot()
        if now<self.start_at:return self.snapshot()
        if not self.armed:
            if pose=='up':self.armed=True;self.phase='up'
            self.cue='push_ready';return self.snapshot()
        if pose=='down' and self.phase=='up':self.phase='down';self.cue='push_raise'
        elif pose=='up' and self.phase=='down':
            if now-self.last_rep>=.3 and self.high_angle-self.low_angle>=max(30,40-(self.tolerance-10)*.25):self.reps+=1;self.last_rep=now
            self.low_angle=self.high_angle=bend
            self.phase='up';self.cue='push_lower'
        elif pose=='up':self.cue='push_lower'
        return self.snapshot()
