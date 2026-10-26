"""Multi-exercise pose heuristics. No exercise recognition or safety certification."""
import math
import statistics

from curl_counter import CurlCounter, elbow_angle
from exercises import CATALOG, thresholds
from form_rules import StableWarning


def required_joints(exercise, side):
    offset = 0 if side == 'left' else 1
    if CATALOG[exercise]['group'] == 'legs':
        return tuple(i+offset for i in (11,23,25,27))
    return tuple(i+offset for i in (11,13,15,23))


def pose_metrics(exercise, side, landmarks, width, height, world=None):
    """Visibility must be checked by caller. Use world geometry only when finite.

    Posture uses estimated 3-D vertical when available (upright camera).
    Valid world segment lengths allow foreshortened front/side views; the 2-D
    fallback still requires adequate projected segment lengths.
    """
    ids = required_joints(exercise, side)
    px = {i:(landmarks[i].x*width,landmarks[i].y*height) for i in ids}
    offset = 0 if side == 'left' else 1
    s, h = 11+offset, 23+offset
    source = '2D'
    xyz = px
    if world and len(world) >= 29 and all(all(math.isfinite(v) for v in
            (world[i].x,world[i].y,world[i].z)) for i in ids):
        xyz = {i:(world[i].x,world[i].y,world[i].z) for i in ids}
        source = 'estimated_3D'
    if source=='2D' and math.dist(px[s],px[h])<35:return None,None
    if source=='estimated_3D' and not .08<math.dist(xyz[s],xyz[h])<1.2:return None,None
    family = CATALOG[exercise]['family']
    torso = (px[h][0]-px[s][0], px[h][1]-px[s][1])
    lean = math.degrees(math.atan2(torso[0],torso[1]))
    if source=='estimated_3D':
        v=tuple(xyz[h][i]-xyz[s][i] for i in range(3));n=math.hypot(*v)
        lean=math.degrees(math.acos(max(-1,min(1,v[1]/n))))
    if family in ('squat','hinge'):
        k, a = 25+offset, 27+offset
        if (source=='2D' and min(math.dist(px[h],px[k]),math.dist(px[k],px[a]))<15) or (source=='estimated_3D' and not all(.05<math.dist(xyz[u],xyz[v])<1.2 for u,v in [(h,k),(k,a)])):
            return None, None
        knee = elbow_angle(xyz[h],xyz[k],xyz[a])
        hip = elbow_angle(xyz[s],xyz[h],xyz[k])
        if knee is None or hip is None:
            return None, None
        return dict(elbow=knee if family=='squat' else hip, lean=lean, arm=0,
                    joint_elbow=180, knee=knee), source
    e, w = 13+offset, 15+offset
    if (source=='2D' and min(math.dist(px[s],px[e]),math.dist(px[e],px[w]))<12) or (source=='estimated_3D' and not all(.05<math.dist(xyz[u],xyz[v])<1.2 for u,v in [(s,e),(e,w)])):
        return None, None
    joint = elbow_angle(xyz[s],xyz[e],xyz[w])
    arm = elbow_angle(xyz[e],xyz[s],xyz[h])
    if joint is None or arm is None:
        return None, None
    return dict(elbow=arm if family=='raise' else joint, lean=lean, arm=arm,
                joint_elbow=joint, knee=180), source


class MotionCoach:
    def __init__(self, exercise, settings, tolerance=10):
        self.exercise = CATALOG[exercise]
        self.family = self.exercise['family']
        self.settings, self.tolerance = settings, tolerance
        self.limits = thresholds(exercise,tolerance)
        self.counter = CurlCounter()
        self.flagged, self.observations = 0, {}
        self.last_rep = 'ยังไม่มีรอบที่จบ'
        self.recalibrate()

    def reset_motion(self):
        self.counter.reset_phase()
        self.filters = {code:StableWarning(self.settings['warning_hold_ms'],self.settings['warning_clear_ms'])
                        for code in ('steady','upper_still','soft_elbow','knee_bend','raise_height')}
        self.cycle_issues = set()
        self.cycle_start = None
        self.tempo_until = 0

    def recalibrate(self):
        self.baseline = None
        self.rack_pending=False
        self.samples = []
        self.lost_since = None
        self.reset_motion()

    def reset(self):
        self.counter.reset()
        self.flagged, self.observations = 0, {}
        self.last_rep = 'ยังไม่มีรอบที่จบ'
        self.reset_motion()

    def base(self):
        return dict(reps=self.counter.reps, flagged=self.flagged,last_rep=self.last_rep,
                    calibrated=self.baseline is not None,calibration=0,form_level='unknown',
                    form_title='รอจัดท่าเริ่มต้น',feedback=[],checks=[],metrics={},
                    thresholds=dict(self.limits,tolerance=self.tolerance),
                    observations=dict(self.observations),phase=self.counter.phase,angle=None)

    def unavailable(self, now, message):
        if self.lost_since is None:
            self.lost_since = now
        self.samples = []
        self.reset_motion()
        if now-self.lost_since >= self.settings['tracking_reset_ms']:
            self.baseline = None
        out = self.base()
        out.update(feedback=[dict(code='frame',text=message)],form_title='ปรับกล้องให้เห็นจุดที่ต้องใช้ก่อนนะ')
        return out

    def posture_ready(self, m):
        lean = abs(m['lean'])
        if self.family == 'row':
            return 25 <= lean <= 125
        if self.family in ('chest_press','triceps'):
            return 55 <= lean <= 125
        if self.family == 'incline_press':
            return 25 <= lean <= 85
        if self.family == 'shoulder_press':
            return lean <= 30 and (m['arm'] >= 45 or m['arm']<=30 and m['joint_elbow']>=140)
        if self.family == 'raise':
            return lean <= 30
        return lean <= 35  # Legs calibrate while upright.

    def update(self, m, now):
        self.lost_since = None
        out = self.base()
        angle = m['elbow']
        out['angle'] = round(angle)
        increasing = self.limits['increasing']
        at_start = angle <= self.limits['start'] if increasing else angle >= self.limits['start']
        if self.baseline is None:
            # No neutral-pose dwell: the counter still requires a full endpoint cycle.
            self.baseline = dict(m)
            self.samples = []
            self.rack_pending = False

        definitions = []
        if self.family not in ('squat','hinge'):
            definitions.append(('steady',abs(m['lean']-self.baseline['lean']),12+self.tolerance,
                                'การแกว่งลำตัว','ลองคุมลำตัวให้นิ่งขึ้นอีกนิด ถ้าต้องเหวี่ยงช่วย ลองลดน้ำหนักนะ'))
        if self.family == 'triceps':
            definitions.append(('upper_still',abs(m['arm']-self.baseline['arm']),12+self.tolerance,
                                'การขยับต้นแขน','คุมต้นแขนให้นิ่ง แล้วขยับด้วยการงอและเหยียดศอกนะ'))
        if self.family == 'raise':
            definitions += [('soft_elbow',max(0,135-m['joint_elbow']),self.tolerance,
                             'การงอศอกมาก','ผ่อนศอกเล็กน้อยและรักษามุมไว้ ไม่ต้องงอแขนเข้าหาตัวมากนะ'),
                            ('raise_height',max(0,m['arm']-95),self.tolerance,
                             'การยกเกินระดับไหล่','ยกประมาณระดับไหล่ก็พอ แล้วค่อย ๆ ลดกลับนะ')]
        if self.family == 'hinge':
            definitions.append(('knee_bend',max(0,140-m['knee']),self.tolerance,
                                'การงอเข่ามาก','ลองดันสะโพกไปหลังและผ่อนเข่าเล็กน้อย ไม่ย่อตัวเป็นสควอตนะ'))
        feedback,checks = [],[]
        for code,value,limit,label,text in definitions:
            detector = self.filters[code]
            was_active = detector.active
            active = detector.update(value>limit+(0 if was_active else 5),now)
            if active and not was_active:
                self.observations[code] = self.observations.get(code,0)+1
            checks.append(dict(code=code,label=label,value=round(value,1),limit=limit,
                               status='warn' if active else 'pending' if value>limit else 'ok'))
            if active:
                feedback.append(dict(code=code,text=text))
                self.cycle_issues.add(code)
        if not checks:
            checks.append(dict(code='range',label='มุมที่ใช้ช่วยนับ (ไม่ใช่คะแนนฟอร์ม)',value=round(angle),
                               limit=None,status='pending'))
        normalized = 180-angle if increasing else angle
        down = 180-self.limits['start'] if increasing else self.limits['start']
        up = 180-self.limits['end'] if increasing else self.limits['end']
        before = self.counter.phase
        if before=='ready' and normalized < down-8 and self.cycle_start is None:
            self.cycle_start = now
        counted = self.counter.update(normalized,now,down,up,self.limits['excursion'])
        if counted:
            if self.cycle_start is not None and now-self.cycle_start<900:
                self.cycle_issues.add('tempo')
                self.tempo_until=now+4500
                self.observations['tempo'] = self.observations.get('tempo',0)+1
            self.flagged += bool(self.cycle_issues)
            self.last_rep = 'นับแล้ว · มีคำแนะนำให้ดูตอนพัก' if self.cycle_issues else 'นับแล้ว ค่อย ๆ ทำต่อได้เลย'
            self.cycle_issues = set()
            self.cycle_start = None
        if now<self.tempo_until:
            feedback.append(dict(code='tempo',text='นับให้แล้วนะ ลองผ่อนจังหวะและควบคุมช่วงลดกลับอีกนิด'))
        out.update(reps=self.counter.reps,flagged=self.flagged,last_rep=self.last_rep,
                   calibrated=True,calibration=100,phase=self.counter.phase,
                   feedback=feedback,checks=checks,form_level='warn' if feedback else 'ok',
                   form_title='ลองปรับอีกนิดนะ' if feedback else 'กำลังติดตามการเคลื่อนไหว',
                   observations=dict(self.observations),metrics=dict(m))
        return out
