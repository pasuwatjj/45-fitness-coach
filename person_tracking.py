"""Conservative short-term geometric association, NOT biometric identification.

Any missing/ambiguous observation latches a slot off. Re-entry requires an
explicit selection and fresh counters/calibration. Never infer identity from
candidate order. Three detections allow a bystander alongside two players.
"""
import math

class PersonLock:
    def __init__(self, count=1):
        self.count=count
        self.slots=[None]*count
        self.status=['waiting']*count
        self.candidates=[]
        self.last_at=None
        self.serial=0

    @staticmethod
    def feature(pose,mode=None):
        if len(pose)!=33:return None
        threshold=.5 if mode is not None else .65
        def visible(i):
            p=pose[i]
            return (p.visibility or 0)>=threshold and math.isfinite(p.x+p.y)
        if mode is None:
            mode='both' if all(visible(i) for i in (11,12,23,24)) else 'left' if all(visible(i) for i in (11,23)) else 'right'
        ids=(11,12,23,24) if mode=='both' else (11,23) if mode=='left' else (12,24)
        if not all(visible(i) for i in ids):return None
        ps=[pose[i] for i in ids]
        cx=sum(p.x for p in ps)/len(ps);cy=sum(p.y for p in ps)/len(ps)
        scale=math.hypot((ps[0].x+ps[1].x-ps[2].x-ps[3].x)/2,(ps[0].y+ps[1].y-ps[2].y-ps[3].y)/2) if mode=='both' else math.hypot(ps[0].x-ps[1].x,ps[0].y-ps[1].y)
        if scale<.07:return None
        return (cx,cy,scale,tuple((p.x,p.y) for p in ps),mode)

    @staticmethod
    def distance(a,b):
        return math.hypot(a[0]-b[0],a[1]-b[1])/max(.1,a[2])

    @classmethod
    def close(cls,a,b):
        return math.hypot(a[0]-b[0],a[1]-b[1])<max(.16,min(a[2],b[2])*.85)

    def invalidate(self):
        for i in range(self.count):
            if self.slots[i] is not None:self.status[i]='lost'

    def update(self,poses,now):
        self.serial+=1
        self.candidates=[(i,f) for i,p in enumerate(poses[:3]) if (f:=self.feature(p)) is not None]
        association_candidates=list(self.candidates)
        for i,p in enumerate(poses[:3]):
            if any(j==i for j,_ in association_candidates):continue
            for old in self.slots:
                if old is not None and (f:=self.feature(p,old[4])) is not None:
                    association_candidates.append((i,f));break
        if self.last_at is not None and now-self.last_at>2.5:self.invalidate()
        self.last_at=now
        selected=[None]*self.count
        # Only an unambiguous, exact-size initial group may auto-lock.
        if all(s=='waiting' for s in self.status) and len(self.candidates)==self.count and not any(self.close(a[1],b[1]) for j,a in enumerate(self.candidates) for b in self.candidates[j+1:]):
            for slot,(idx,f) in enumerate(sorted(self.candidates,key=lambda row:row[1][0])):
                self.slots[slot]=f;self.status[slot]='locked';selected[slot]=idx
            return selected
        proposals=[]
        for slot,old in enumerate(self.slots):
            if self.status[slot]!='locked':continue
            ranked=sorted((self.distance(old,f),idx,f) for idx,_ in association_candidates if (f:=self.feature(poses[idx],old[4])) is not None and .65<f[2]/old[2]<1.5)
            if not ranked or ranked[0][0]>.42:
                self.status[slot]='lost';continue
            _,idx,f=ranked[0]
            if (len(ranked)>1 and ranked[1][0]-ranked[0][0]<.35) or any(self.close(f,g) for j,g in association_candidates if j!=idx):
                self.status[slot]='ambiguous';continue
            proposals.append((slot,idx,f))
        for slot,idx,f in proposals:
            if sum(other==idx for _,other,_ in proposals)>1:self.status[slot]='ambiguous'
            else:self.slots[slot]=f;selected[slot]=idx
        return selected

    def select(self,slot,x,y,now):
        if type(slot) is not int or not 0<=slot<self.count or self.last_at is None or now-self.last_at>2:raise ValueError('Refresh camera and select again / รอภาพใหม่แล้วเลือกอีกครั้ง')
        ranked=sorted((math.hypot(f[0]-x,f[1]-y),idx,f) for idx,f in self.candidates)
        if not ranked or ranked[0][0]>.08:raise ValueError('Person moved; select again / คนขยับแล้ว กรุณาเลือกใหม่')
        _,idx,f=ranked[0]
        if any(self.close(f,g) for j,g in self.candidates if j!=idx):raise ValueError('Separate people before selecting / ยืนแยกกันก่อนเลือก')
        if any(i!=slot and self.status[i]=='locked' and self.distance(old,f)<.42 for i,old in enumerate(self.slots) if old):raise ValueError('Already assigned to another player / คนนี้อยู่ช่องผู้เล่นอื่นแล้ว')
        self.slots[slot]=f;self.status[slot]='locked'
        return idx

    def snapshot(self):
        return dict(status=list(self.status),anchors=[dict(x=f[0],y=f[1],scale=f[2],mode=f[4]) if f is not None else None for f in self.slots],candidates=[dict(x=round(f[0],4),y=round(f[1],4),index=i) for i,f in self.candidates])
