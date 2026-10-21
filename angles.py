"""Passive set statistics. Never changes thresholds, counters, or camera lifecycle."""
import json, math, statistics
from datetime import datetime,timezone,timedelta

class SetAngles:
    def __init__(self):self.groups={};self.cycles={};self.last={}
    def sample(self,side,metrics,source,now):
        # Limit storage/weighting to approximately 10 samples/second per side.
        if now-self.last.get(side,-1e9)<100:return
        if now-self.last.get(side,now)>1250:
            for (s,_),c in self.cycles.items():
                if s==side:c['points']=[]
        self.last[side]=now
        bucket=self.groups.setdefault(side,{}).setdefault(source,{})
        for key in ('elbow','arm','lean'):
            x=metrics.get(key)
            if not isinstance(x,(int,float)) or not math.isfinite(x):continue
            b=bucket.setdefault(key,[0,0.,0.,x,x]);b[0]+=1;delta=x-b[1];b[1]+=delta/b[0];b[2]+=delta*(x-b[1]);b[3]=min(b[3],x);b[4]=max(b[4],x)
        x=metrics.get('elbow')
        if isinstance(x,(int,float)) and math.isfinite(x):
            c=self.cycles.setdefault((side,source),{'points':[],'ranges':[]})
            if len(c['points'])<1200:c['points'].append(x)
    def completed(self,side,source):
        c=self.cycles.get((side,source))
        if c and c['points']:
            if len(c['ranges'])<500:c['ranges'].append([min(c['points']),max(c['points'])])
            c['points']=[]
    def report(self):
        rows=[]
        for side,sources in self.groups.items():
            for source,metrics in sources.items():
                values={key:dict(samples=b[0],mean=round(b[1],1),sd=round(math.sqrt(b[2]/b[0]),1),minimum=round(b[3],1),maximum=round(b[4],1)) for key,b in metrics.items()}
                ranges=self.cycles.get((side,source),{}).get('ranges',[])
                row=dict(side=side,source=source,metrics=values,completed_attempts=len(ranges))
                if ranges:
                    for i,label in [(0,'low'),(1,'high')]:
                        v=[r[i] for r in ranges];row[label]=dict(mean=round(statistics.mean(v),1),sd=round(statistics.pstdev(v),1))
                rows.append(row)
        return rows

def schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS set_angles(id TEXT PRIMARY KEY,profile_id INTEGER NOT NULL,exercise TEXT NOT NULL,day TEXT NOT NULL,data TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)')

def save(store,set_id,pid,exercise,tracker):
    rows=tracker.report()
    if not rows:return
    day=datetime.now(timezone(timedelta(hours=7))).date().isoformat()
    with store.lock,store.connect() as db:
        schema(db)
        db.execute('INSERT INTO set_angles(id,profile_id,exercise,day,data) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(set_id,pid,exercise,day,json.dumps(rows)))

def history(store,pid,day=None):
    with store.lock,store.connect() as db:
        schema(db)
        dates=[r[0] for r in db.execute('SELECT DISTINCT day FROM set_angles WHERE profile_id=? ORDER BY day DESC',(pid,))]
        chosen=day or (dates[0] if dates else None)
        rows=[dict(r) for r in db.execute('SELECT * FROM set_angles WHERE profile_id=? AND day=? ORDER BY created_at,id',(pid,chosen))]
    for r in rows:r['data']=json.loads(r['data'])
    return dict(dates=dates,day=chosen,sets=rows)
