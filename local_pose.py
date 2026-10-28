"""Bounded untrusted browser landmarks. Rewards remain server-calculated."""
import math
from types import SimpleNamespace as NS

def parse(data):
    if not isinstance(data,dict):raise ValueError('Invalid pose payload')
    w,h=data.get('width'),data.get('height')
    if type(w) is not int or type(h) is not int or not 32<=w<=960 or not 32<=h<=960:raise ValueError('Invalid frame size')
    def points(rows,count,world=False):
        if not isinstance(rows,list) or len(rows)!=count:raise ValueError('Invalid landmark count')
        result=[]
        for r in rows:
            if not isinstance(r,dict):raise ValueError('Invalid landmark')
            values=[r.get(k) for k in ('x','y','z')]
            if any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>10 for v in values):raise ValueError('Invalid coordinates')
            visibility=r.get('visibility',1)
            if type(visibility) not in (int,float) or not math.isfinite(visibility) or not 0<=visibility<=1:raise ValueError('Invalid visibility')
            result.append(NS(x=values[0],y=values[1],z=values[2],visibility=visibility,presence=visibility))
        return result
    poses=data.get('pose',[]);world=data.get('world',[])
    if not isinstance(poses,list) or not isinstance(world,list):raise ValueError('Invalid pose')
    pose=points(poses,33) if poses else []
    world=points(world,33,True) if world else []
    if world and not pose:raise ValueError('World pose without image pose')
    hs=data.get('hands',[]);hw=data.get('handWorld',[])
    if not isinstance(hs,list) or not isinstance(hw,list) or len(hs)>2 or len(hs)!=len(hw):raise ValueError('Invalid hands')
    hands=NS(multi_hand_landmarks=[NS(landmark=points(x,21)) for x in hs],multi_hand_world_landmarks=[NS(landmark=points(x,21,True)) for x in hw])
    all_poses=[pose] if pose else [];all_world=[world] if world else []
    if 'poses' in data:
        rows=data['poses'];worlds=data.get('worlds',[])
        if not isinstance(rows,list) or not isinstance(worlds,list) or len(rows)>3 or len(rows)!=len(worlds):raise ValueError('Invalid pose candidates')
        all_poses=[points(row,33) for row in rows]
        all_world=[points(row,33,True) if row else [] for row in worlds]
    return w,h,NS(pose_landmarks=all_poses,pose_world_landmarks=all_world),hands
