"""Reject transient, isolated landmark jumps; never snap a joint to anatomy.
Persistent model bias cannot be corrected by this temporal quality check.
"""
import copy,math
NEIGHBORS={11:(12,13,23),12:(11,14,24),13:(11,15),14:(12,16),23:(11,24,25),24:(12,23,26)}
class PoseSanity:
 def __init__(self):self.reset()
 def reset(self):self.previous=None;self.at=None;self.pending={};self.suppressed=[]
 def apply(self,pose,now,aspect=1):
  self.suppressed=[]
  if not pose:self.reset();return pose
  out=copy.deepcopy(pose)
  valid=lambda p:p.visibility is not None and p.visibility>=.6 and all(math.isfinite(v) for v in (p.x,p.y))
  xy=lambda p:(p.x*aspect,p.y)
  if self.previous is not None and 0<=now-self.at<.65:
   old=self.previous
   for i,neighbors in NEIGHBORS.items():
    if not valid(pose[i]) or not valid(old[i]):continue
    ns=[j for j in neighbors if valid(pose[j]) and valid(old[j])]
    if len(ns)<2:continue
    dx=sum((pose[j].x-old[j].x)*aspect for j in ns)/len(ns);dy=sum(pose[j].y-old[j].y for j in ns)/len(ns)
    residual=math.hypot((pose[i].x-old[i].x)*aspect-dx,pose[i].y-old[i].y-dy)
    distorted=0
    for j in ns:
     before=math.dist(xy(old[i]),xy(old[j]));after=math.dist(xy(pose[i]),xy(pose[j]))
     if before>.06 and (after/before>1.9 or after/before<.45):distorted+=1
    if residual>.13 and distorted>=2:
     previous=self.pending.get(i)
     if previous is None or math.dist(xy(previous[0]),xy(pose[i]))>.07:self.pending[i]=(copy.copy(pose[i]),now,1)
     else:self.pending[i]=(copy.copy(pose[i]),previous[1],previous[2]+1)
     pending=self.pending[i]
     if pending[2]<3 or now-pending[1]<.12:
      out[i].visibility=0;out[i].presence=0;self.suppressed.append(i);continue
    self.pending.pop(i,None)
  saved=copy.deepcopy(pose)
  if self.previous:
   for i in self.suppressed:saved[i]=copy.copy(self.previous[i])
  self.previous=saved;self.at=now
  return out
