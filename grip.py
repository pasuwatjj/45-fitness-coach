"""Conservative palm-plane heuristic. Not a validated grip/dumbbell classifier."""
import math
import numpy as np
from curl_counter import elbow_angle
from form_rules import StableWarning


def unit(v):
    n=float(np.linalg.norm(v))
    return v/n if n>1e-6 and np.isfinite(v).all() else None


def xyz(p):return np.array([p.x,p.y,p.z],dtype=float)


def assess_grip(side, pose, world, hands, width, height):
    unknown=dict(kind='unknown',angle=None,wrist=None)
    if not pose or not world or not hands or not getattr(hands,'multi_hand_landmarks',None):return unknown
    off=0 if side=='left' else 1
    ids=(11+off,13+off,15+off)
    if any(getattr(pose[i],'visibility',0)<.7 for i in (*ids,11,12,23,24)):return unknown
    wrist=pose[ids[2]]
    candidates=[]
    for i,lm in enumerate(hands.multi_hand_landmarks):
        p=lm.landmark[0]
        d=math.hypot((p.x-wrist.x)*width,(p.y-wrist.y)*height)
        candidates.append((d,i))
    d,index=min(candidates)
    arm_size=math.hypot((pose[ids[1]].x-wrist.x)*width,(pose[ids[1]].y-wrist.y)*height)
    if d>max(20,arm_size*.3):return unknown
    h=hands.multi_hand_landmarks[index].landmark
    if any(not 0<=h[i].x<=1 or not 0<=h[i].y<=1 for i in (0,5,9,17)):return unknown
    span=math.hypot((h[5].x-h[17].x)*width,(h[5].y-h[17].y)*height)
    if span<12:return unknown
    wrist_angle=elbow_angle((pose[ids[1]].x*width,pose[ids[1]].y*height),
        (wrist.x*width,wrist.y*height),(h[9].x*width,h[9].y*height))
    unknown['wrist']=wrist_angle
    elbow=elbow_angle(*(xyz(world[i]) for i in ids))
    if elbow is None or not 125<=elbow<=178:return unknown
    hand_world=getattr(hands,'multi_hand_world_landmarks',None)
    if not hand_world or len(hand_world)<=index:return unknown
    hw=hand_world[index].landmark
    normal=unit(np.cross(xyz(hw[5])-xyz(hw[0]),xyz(hw[17])-xyz(hw[0])))
    side_axis=unit(xyz(world[12])-xyz(world[11]))
    down_axis=unit((xyz(world[23])+xyz(world[24])-xyz(world[11])-xyz(world[12]))/2)
    if normal is None or side_axis is None or down_axis is None:return unknown
    front=unit(np.cross(side_axis,down_axis))
    if front is None:return unknown
    # Absolute normal deliberately does not claim pronated vs supinated certainty.
    facing=abs(float(np.dot(normal,front)));inward=abs(float(np.dot(normal,side_axis)))
    if max(facing,inward)<.8 or abs(facing-inward)<.35:return unknown
    return dict(kind='curl_plane' if facing>inward else 'neutral_plane',
                angle=round(math.degrees(math.acos(min(1,facing)))),wrist=wrist_angle)


class GripCoach:
    def __init__(self):
        self.filters={a:{k:StableWarning(900,650) for k in ('grip','wrist','shoulders')} for a in ('left','right')}

    def update(self,side,exercise,result,now):
        expected='neutral_plane' if exercise=='hammer_curl' else 'curl_plane'
        known=result['kind']!='unknown'
        wrong=known and result['kind']!=expected
        f=self.filters[side]['grip']
        # Unknown is not evidence of a correct grip and must not inherit a prior verdict.
        if not known:f.active=False;f.last=None
        active=f.update(wrong,now) if known else False
        checks=[dict(code='grip',label='การจับมือ (ทดลอง)',status='warn' if active else 'ok' if known and not wrong else 'pending' if known else 'unknown',
            value=result['angle'],limit=None,display='ปรับการจับก่อนนับ' if active else 'ระนาบมือสอดคล้อง' if known and not wrong else 'กำลังดูการจับ' if known else 'ยังยืนยันไม่ได้ · ดูตอนแขนลง')]
        feedback=[]
        if active:feedback.append(dict(code='grip_hammer' if exercise=='hammer_curl' else 'grip_curl',text='ลองจับแบบนิ้วโป้งชี้ขึ้น ฝ่ามือเข้าหากันนะ' if exercise=='hammer_curl' else 'ลองหงายฝ่ามือไปด้านหน้า ศอกอยู่ข้างตัวนะ'))
        wa=result.get('wrist');wf=self.filters[side]['wrist']
        wrist_active=wf.update(wa<145 if wa is not None else False,now)
        checks.append(dict(code='wrist',label='แนวข้อมือ',status='unknown' if wa is None else 'warn' if wrist_active else 'ok',value=round(wa) if wa is not None else None,limit=145))
        if wrist_active:feedback.append(dict(code='wrist',text='ลองรักษาข้อมือให้ต่อแนวกับปลายแขน ไม่พับช่วยยกนะ'))
        return dict(blocked=active,checks=checks,feedback=feedback,verified=known and not wrong)

    def shoulders(self, side, pose, width, height, now):
        if not pose or any(getattr(pose[i],'visibility',0)<.75 for i in (11,12,23,24)):
            return None
        dx=(pose[12].x-pose[11].x)*width
        dy=(pose[12].y-pose[11].y)*height
        torso=math.hypot((pose[11].x-pose[23].x)*width,(pose[11].y-pose[23].y)*height)
        if abs(dx)<torso*.45:return None # side view cannot reliably assess level shoulders
        angle=abs(math.degrees(math.atan2(dy,abs(dx))))
        active=self.filters[side]['shoulders'].update(angle>18,now)
        return dict(code='shoulders',label='ระดับไหล่',status='warn' if active else 'ok',value=round(angle),limit=18)
