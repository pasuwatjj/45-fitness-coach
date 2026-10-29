"""Conservative short-term geometric association, NOT biometric identification.

Missing observations pause counting. Solo tracking can reacquire a stable
nearby target; overlapping people still require explicit reselection. Never infer identity from
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
        self.missing_since=[None]*count
        self.pending=[None]*count
        self.solo_search=None
        self.empty_since=None

    @staticmethod
    def feature(pose,mode=None):
        if len(pose)!=33:return None
        threshold=.45 if mode is not None else .6
        def visible(i):
            p=pose[i]
            return (p.visibility or 0)>=threshold and math.isfinite(p.x+p.y) and -.15<=p.x<=1.15 and -.15<=p.y<=1.15
        # A close-up arm workout need not show hips. Never use wrists/elbows as
        # identity anchors: they deliberately move through a large range.
        if all(visible(i) for i in (11,12,23,24)):ids=(11,12,23,24);mode='both'
        elif all(visible(i) for i in (11,12)):ids=(11,12);mode='shoulders'
        elif all(visible(i) for i in (11,23)):ids=(11,23);mode='left'
        elif all(visible(i) for i in (12,24)):ids=(12,24);mode='right'
        elif visible(12) and visible(8):ids=(12,8);mode='head_right'
        elif visible(11) and visible(7):ids=(11,7);mode='head_left'
        else:return None
        ps=[pose[i] for i in ids]
        cx=sum(p.x for p in ps)/len(ps);cy=sum(p.y for p in ps)/len(ps)
        scale=math.hypot((ps[0].x+ps[1].x-ps[2].x-ps[3].x)/2,(ps[0].y+ps[1].y-ps[2].y-ps[3].y)/2) if mode=='both' else math.hypot(ps[0].x-ps[1].x,ps[0].y-ps[1].y)
        if scale<.035:return None
        return (cx,cy,scale,tuple((i,pose[i].x,pose[i].y) for i in ids),mode)

    @staticmethod
    def distance(a,b):
        old={i:(x,y) for i,x,y in a[3]};common=[math.hypot(x-old[i][0],y-old[i][1]) for i,x,y in b[3] if i in old]
        if not common:return float('inf')
        return sum(common)/len(common)/max(.1,a[2])

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
        if self.last_at is not None and now-self.last_at>3.5:self.invalidate()
        self.last_at=now
        selected=[None]*self.count
        if self.count==1:
            if not association_candidates:
                if self.empty_since is None:self.empty_since=now
            elif len(association_candidates)==1:
                idx,f=association_candidates[0]
                old=self.slots[0]
                separated_return=self.empty_since is not None and now-self.empty_since>=.8
                searching=self.status[0] in ('lost','ambiguous','recovering') or separated_return
                if searching:
                    candidate=self.solo_search
                    if candidate is None or self.distance(candidate[0],f)>.4:
                        self.solo_search=(f,now,1)
                    else:self.solo_search=(f,candidate[1],candidate[2]+1)
                    candidate=self.solo_search
                    # A stable single target anywhere can restart association.
                    # Partial motion was discarded on the intervening empty frames.
                    if candidate[2]>=4 and now-candidate[1]>=.65:
                        self.slots[0]=f;self.status[0]='locked'
                        self.pending[0]=None;self.missing_since[0]=None
                        self.empty_since=None;self.solo_search=None
                        return [idx]
            else:self.solo_search=None
            if not association_candidates:self.solo_search=None

        # Only an unambiguous, exact-size initial group may auto-lock.
        if all(s=='waiting' for s in self.status) and len(self.candidates)==self.count and not any(self.close(a[1],b[1]) for j,a in enumerate(self.candidates) for b in self.candidates[j+1:]):
            for slot,(idx,f) in enumerate(sorted(self.candidates,key=lambda row:row[1][0])):
                self.slots[slot]=f;self.status[slot]='locked';selected[slot]=idx
            return selected
        proposals=[]
        for slot,old in enumerate(self.slots):
            if self.status[slot] not in (('locked','recovering','lost') if self.count==1 else ('locked','recovering')):continue
            if old is None:continue
            recovering=self.status[slot]!='locked'
            if any(self.close(a[1],b[1]) and min(self.distance(old,a[1]),self.distance(old,b[1]))<1.5 for j,a in enumerate(association_candidates) for b in association_candidates[j+1:]):
                self.status[slot]='ambiguous';continue
            ranked=sorted((self.distance(old,f),idx,f) for idx,_ in association_candidates if (f:=self.feature(poses[idx],old[4])) is not None and (f[4]!=old[4] or .5<f[2]/old[2]<1.8))
            if not ranked or ranked[0][0]>(1.2 if self.count==1 else .42):
                self.pending[slot]=None
                self.missing_since[slot]=now if self.missing_since[slot] is None else self.missing_since[slot]
                self.status[slot]='recovering' if self.count==1 or now-self.missing_since[slot]<.6 else 'lost';continue
            _,idx,f=ranked[0]
            if (len(ranked)>1 and ranked[1][0]-ranked[0][0]<.35) or any(self.close(f,g) for j,g in association_candidates if j!=idx):
                self.status[slot]='ambiguous';continue
            if self.count==1 and (recovering or ranked[0][0]>.42):
                # Small dropouts can continue, but long gaps/large steps must
                # show a spatially stable target over multiple observations.
                short=self.missing_since[slot] is not None and now-self.missing_since[slot]<.6 and ranked[0][0]<=.42
                if not short:
                    pending=self.pending[slot]
                    if pending is None or self.distance(pending[0],f)>.3:
                        self.pending[slot]=(f,now,1)
                    else:self.pending[slot]=(f,pending[1],pending[2]+1)
                    pending=self.pending[slot]
                    if pending[2]<3 or now-pending[1]<.2:
                        self.status[slot]='recovering';continue
            proposals.append((slot,idx,f))
        for slot,idx,f in proposals:
            if sum(other==idx for _,other,_ in proposals)>1:self.status[slot]='ambiguous'
            else:
                if self.count>1 and self.missing_since[slot] is not None and now-self.missing_since[slot]>=.6:
                    self.status[slot]='lost';continue
                self.pending[slot]=None;self.slots[slot]=f;self.status[slot]='locked';self.missing_since[slot]=None;selected[slot]=idx
                if self.count==1:self.solo_search=None;self.empty_since=None
        return selected

    def select(self,slot,x,y,now):
        if type(slot) is not int or not 0<=slot<self.count or self.last_at is None or now-self.last_at>2:raise ValueError('Refresh camera and select again / รอภาพใหม่แล้วเลือกอีกครั้ง')
        ranked=sorted((math.hypot(f[0]-x,f[1]-y),idx,f) for idx,f in self.candidates)
        if not ranked or ranked[0][0]>.08:raise ValueError('Person moved; select again / คนขยับแล้ว กรุณาเลือกใหม่')
        _,idx,f=ranked[0]
        if any(self.close(f,g) for j,g in self.candidates if j!=idx):raise ValueError('Separate people before selecting / ยืนแยกกันก่อนเลือก')
        if any(i!=slot and self.status[i]=='locked' and self.distance(old,f)<.42 for i,old in enumerate(self.slots) if old):raise ValueError('Already assigned to another player / คนนี้อยู่ช่องผู้เล่นอื่นแล้ว')
        self.pending[slot]=None;self.slots[slot]=f;self.status[slot]='locked';self.missing_since[slot]=None
        return idx

    def snapshot(self):
        return dict(status=list(self.status),anchors=[dict(x=f[0],y=f[1],scale=f[2],mode=f[4],points=f[3]) if f is not None else None for f in self.slots],candidates=[dict(x=round(f[0],4),y=round(f[1],4),index=i) for i,f in self.candidates])
