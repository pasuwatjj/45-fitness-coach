"""Conservative experimental motion-plane rules, not clinical form assessment."""
import math
import numpy as np
from curl_counter import elbow_angle
from exercises import CATALOG

MESSAGES={
 'curl_path':('งอปลายแขนเข้าด้านหน้าหาไหล่ ไม่กางหรือยกไปด้านหลังนะ','Curl your forearm forward toward your shoulder, not sideways or behind you.'),
 'upper_position':('ให้ต้นแขนอยู่ข้างลำตัว ไม่ยกศอกหนีตัวมากนะ','Keep your upper arm beside your body; avoid moving your elbow far away.'),
 'upper_still':('คุมต้นแขนให้นิ่งในแนวเริ่มต้นของท่านี้ ไม่แกว่งศอกช่วยนะ','Keep your upper arms steady in this exercise’s starting position; avoid swinging the elbows.'),
 'elbow_shape':('ผ่อนศอกเล็กน้อย ไม่งอศอกเข้าหาตัวมากระหว่างยกแขนนะ','Keep a slight elbow bend rather than curling the forearm toward you during the raise.'),
 'raise_height':('ยกประมาณระดับไหล่ แล้วลดกลับอย่างควบคุมนะ','Raise to around shoulder level, then lower with control.'),
 'body_position':('จัดแนวลำตัวตามท่านี้ แล้วคุมตัวไม่โยกช่วยนะ','Reset your torso position for this exercise and avoid swinging.'),
 'row_path':('ดึงศอกไปด้านหลังเข้าหาสะโพก ไม่งอแขนมาด้านหน้านะ','Pull your elbow back toward your hip rather than curling forward.'),
 'press_path':('ดันมือขึ้นตามแนวท่านี้ ให้ข้อมืออยู่เหนือศอกนะ','Press along the exercise direction and keep wrists above elbows.'),
 'raise_path':('ยกแขนตามทิศของท่าที่เลือก ไม่ยกสลับด้านหน้าและด้านข้างนะ','Raise in the direction of the selected exercise, not the other direction.'),
 'leg_position':('คุมแนวลำตัวและการงอเข่าตามท่านี้ก่อนทำรอบต่อไปนะ','Check your torso position and knee bend before the next rep.'),
 'unverified':('ยังประเมินทิศทางไม่ได้ จัดกล้องให้เห็นไหล่ สะโพก และแขนชัดก่อนนะ','Direction is unclear. Show your shoulders, hips and working arm clearly.'),
 'wrist':('ข้อมือตรงต่อกับปลายแขน ไม่พับช่วยยกนะ','Keep the wrist aligned with the forearm.'),
 'grip':('ปรับการจับตามภาพตัวอย่างก่อนรอบถัดไปนะ','Adjust your grip to match the guide before the next rep.')}

def unit(v):
    n=float(np.linalg.norm(v))
    return v/n if n>.04 and np.isfinite(v).all() else None

def geometry(exercise,side,pose,world,m):
    """Unknown is distinct from a confirmed mismatch. Thresholds have margin."""
    off=0 if side=='left' else 1
    ids=[11,12,23,24,11+off,13+off,15+off]
    if CATALOG[exercise]['group']=='legs':ids=[11,12,23,24,25+off,27+off]
    if not pose or not world or len(pose)<=max(ids) or len(world)<=max(ids):return False,[]
    if any(pose[i].visibility is None or pose[i].visibility<.55 for i in ids):return False,[]
    xyz=lambda i:np.array([world[i].x,world[i].y,world[i].z],dtype=float)
    if not all(np.isfinite(xyz(i)).all() for i in ids):return False,[]
    up=unit((xyz(11)+xyz(12)-xyz(23)-xyz(24))/2)
    side_axis=unit(xyz(12)-xyz(11))
    if up is None or side_axis is None:return False,[]
    front=unit(np.cross(up,side_axis))
    if front is None:return False,[]
    # Anatomical left/right fixes the normal's sign; do not flip from noisy nose depth.
    family=CATALOG[exercise]['family'];bad=[]
    lean=math.degrees(math.acos(float(np.clip(np.dot(up,np.array([0.,-1.,0.])), -1, 1))))
    if family in ('curl','raise','shoulder_press') and lean>32:bad.append('body_position')
    if family=='row' and not 20<=lean<=130:bad.append('body_position')
    if family in ('chest_press','triceps') and not 45<=lean<=135:bad.append('body_position')
    if family=='incline_press' and not 20<=lean<=95:bad.append('body_position')
    if family in ('squat','hinge'):
        if family=='squat' and lean>65:bad.append('leg_position')
        if family=='hinge' and m.get('knee',180)<110:bad.append('leg_position')
        return True,bad
    upper=unit(xyz(13+off)-xyz(11+off));fore=unit(xyz(15+off)-xyz(13+off))
    if upper is None or fore is None:return False,[]
    joint=elbow_angle(xyz(11+off),xyz(13+off),xyz(15+off))
    arm=math.degrees(math.acos(float(np.clip(np.dot(upper,-up),-1,1))))
    forward=float(np.dot(fore,front));lateral=abs(float(np.dot(fore,side_axis)))
    if family=='curl':
        # Body-relative axes let the whole person turn without being penalized.
        # A small upper-arm drift is advice; only a clear mismatch rejects a rep.
        if arm>45 or float(np.dot(upper,front))>.65:bad.append('upper_position')
        if joint is not None and joint<125 and (forward<-.25 or lateral>.82):bad.append('curl_path')
    elif family=='row':
        if joint is not None and joint<110 and float(np.dot(upper,front))>.45:bad.append('row_path')
    elif family in ('chest_press','incline_press','triceps'):
        if joint is not None and joint>140 and float(np.dot(fore,front))<.15:bad.append('press_path')
    elif family=='shoulder_press':
        if joint is not None and joint>140 and float(np.dot(fore,up))<.35:bad.append('press_path')
    elif family=='raise' and arm>45:
        if exercise=='front_raise' and (float(np.dot(upper,front))<.25 or abs(float(np.dot(upper,side_axis)))>.78):bad.append('raise_path')
        if exercise=='lateral_raise' and (abs(float(np.dot(upper,side_axis)))<.35 or float(np.dot(upper,front))<-.3):bad.append('raise_path')
    return True,bad

class AttemptGate:
    def __init__(self):
        self.since={};self.bad=set();self.evidence=0;self.active=False
    def observe(self,known,codes,now,moving):
        active=[]
        for code in list(self.since):
            if code not in codes:self.since.pop(code)
        for code in codes:
            self.since.setdefault(code,now)
            if now-self.since[code]>=100:active.append(code)
        if moving:
            self.active=True
            if known:self.evidence+=1
            self.bad.update(active)
        return active
    def finish(self):
        result=('rejected',sorted(self.bad)) if self.bad else ('accepted',[]) if self.evidence>=2 else ('unverified',['unverified'])
        self.bad=set();self.evidence=0;self.active=False
        return result
    def lost(self):
        self.bad=set();self.evidence=0;self.since={};self.active=False
