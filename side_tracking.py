"""Short confidence hysteresis using current observed points, never extrapolated joints."""
import math

class SideTracking:
    def __init__(self): self.last={}
    def clear(self,side=None):
        if side is None:self.last.clear()
        else:self.last.pop(side,None)
    def accepts(self,side,points,ids,now):
        if not points or len(points)<=max(ids):self.clear(side);return False
        ps=[points[i] for i in ids]
        def valid(p,threshold):
            return all(isinstance(v,(int,float)) and math.isfinite(v) for v in (p.x,p.y,getattr(p,'visibility',None),getattr(p,'presence',None))) and 0<=p.x<=1 and 0<=p.y<=1 and min(p.visibility,p.presence)>=threshold
        if all(valid(p,.65) for p in ps):
            self.last[side]=(now,tuple(ids),[(p.x,p.y) for p in ps]);return True
        old=self.last.get(side)
        # Only bridge a short confidence dip after a strong observation, with
        # visible current points and bounded movement. Missing points cancel.
        if old and old[1]==tuple(ids) and 0<=now-old[0]<=400 and all(valid(p,.5) for p in ps) and all(math.dist((p.x,p.y),q)<=.12 for p,q in zip(ps,old[2])):return True
        self.clear(side);return False
