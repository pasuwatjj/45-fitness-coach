"""2D coaching heuristics for a conventional standing dumbbell curl.

Qualitative technique: Mayo Clinic / NASM (see README).
Numeric cutoffs are adjustable engineering settings, NOT validated clinical
limits. A single view cannot certify safety or evaluate spinal/wrist alignment.
"""
import math
import statistics

from curl_counter import CurlCounter, elbow_angle


def vector_angle(u, v):
    return elbow_angle(u, (0, 0), v)


def measurements(shoulder, elbow, wrist, hip=None):
    torso = (hip[0] - shoulder[0], hip[1] - shoulder[1]) if hip is not None else (0, 1)
    upper = (elbow[0] - shoulder[0], elbow[1] - shoulder[1])
    length = math.hypot(*torso)
    if (hip is not None and length < 40) or math.hypot(*upper) < 15:
        return None
    angle = elbow_angle(shoulder, elbow, wrist)
    arm = vector_angle(upper, torso)
    if angle is None or arm is None:
        return None
    return dict(elbow=angle, lean=math.degrees(math.atan2(torso[0], torso[1])) if hip is not None else None, arm=arm)


class StableWarning:
    """Hold and release durations suppress one-frame pose noise."""
    def __init__(self, hold, clear):
        self.hold, self.clear = hold, clear
        self.active = False
        self.last = None
        self.since = 0

    def update(self, bad, now):
        if bad != self.last:
            self.last, self.since = bad, now
        if now - self.since >= (self.hold if bad else self.clear):
            self.active = bad
        return self.active


class FormCoach:
    def __init__(self, settings, tolerance=10):
        self.settings = dict(settings)
        self.settings['minimum_rep_excursion_deg']=max(30,settings['minimum_rep_excursion_deg']-max(0,tolerance-10)*.35)
        self.tolerance = tolerance
        self.preferred_down = settings['extension_target_deg'] - tolerance
        self.preferred_up = settings['flexion_target_deg'] + tolerance
        self.down = self.preferred_down - settings['extension_count_grace_deg']
        self.up = min(105, settings['curl_target_deg']+tolerance) if 'curl_target_deg' in settings else min(100, self.preferred_up + settings['flexion_count_grace_deg'])
        self.down=max(self.down,self.up+25)
        self.lean_limit = settings['torso_base_limit_deg'] + tolerance
        self.arm_limit = settings['upper_arm_base_limit_deg'] + tolerance
        self.counter = CurlCounter()
        self.flagged = 0
        self.last_rep = 'ยังไม่มีรอบที่จบ'
        self.observations = {}
        self.recalibrate()

    def recalibrate(self):
        self.baseline = None
        self.samples = []
        self.lost_since = None
        self.reset_motion()

    def reset_motion(self):
        self.counter.reset_phase()
        self.filters = {key: StableWarning(self.settings['warning_hold_ms'],
                        self.settings['warning_clear_ms']) for key in ('torso', 'arm')}
        self.cycle_issues = set()
        self.lift_start = self.lower_start = None
        self.lift_duration = None
        self.minimum = 180
        self.maximum = 0
        self.rising = False
        self.last_angle = None
        self.range_peak = 180
        self.range_valley = 0
        self.last_top = None
        self.notice = None
        self.notice_until = 0
        self.last_note = {}
        self.partial_attempts = {}

    def reset(self):
        self.counter.reset()
        self.flagged = 0
        self.last_rep = 'ยังไม่มีรอบที่จบ'
        self.observations = {}
        self.reset_motion()

    def base(self):
        return dict(reps=self.counter.reps, flagged=self.flagged, last_rep=self.last_rep,
                    calibrated=self.baseline is not None, calibration=0,
                    form_level='unknown', form_title='รอภาพช่วงบน', feedback=[], checks=[],
                    metrics={}, thresholds=dict(down=self.down, up=self.up,
                    lean=self.lean_limit, arm=self.arm_limit, tolerance=self.tolerance,
                    preferred_down=self.preferred_down, preferred_up=self.preferred_up),
                    observations=dict(self.observations),
                    phase=self.counter.phase, angle=None)

    def unavailable(self, now, message):
        if self.lost_since is None:
            self.lost_since = now
        self.samples = []
        self.reset_motion()
        if now - self.lost_since >= self.settings['tracking_reset_ms']:
            self.baseline = None
        out = self.base()
        out.update(message=message, form_title='ภาพไม่ครบ — ยังประเมินไม่ได้',
                   feedback=[dict(code='tracking', text=message)])
        return out

    def note(self, code, text, now, deferred=False):
        self.observations[code] = self.observations.get(code, 0) + 1
        if deferred:
            self.partial_attempts[code] = self.partial_attempts.get(code, 0) + 1
            if self.partial_attempts[code] < self.settings['partial_attempts_before_live_tip']:
                return
        if now - self.last_note.get(code, -100000) < self.settings['feedback_cooldown_ms']:
            return
        self.last_note[code] = now
        self.notice = dict(code=code, text=text)
        self.notice_until = now + 2500

    def update(self, m, now):
        self.lost_since = None
        out = self.base()
        out['angle'] = round(m['elbow'])
        if self.baseline is None:
            # v35: capture a reference immediately; absolute checks still apply.
            self.baseline = dict(m)
            self.samples = []
            out['calibrated'] = True
            out['calibration'] = 100

        lean = (max(abs(m['lean']), abs(m['lean'] - self.baseline['lean']))
                if m['lean'] is not None and self.baseline['lean'] is not None else None)
        arm = max(m['arm'], abs(m['arm'] - self.baseline['arm']))
        checks = []
        feedback = []
        definitions = [
            ('torso', lean, self.lean_limit, 'ลำตัว',
             'ลองกลับมายืนตัวตรง ผ่อนจังหวะและคุมลำตัวให้นิ่งขึ้นอีกนิดนะ'),
            ('arm', arm, self.arm_limit, 'ต้นแขน / ศอก',
             'ลองให้ศอกอยู่ใกล้ลำตัวอีกนิด แล้วค่อย ๆ ยกด้วยการงอศอกนะ')]
        for code, value, limit, label, text in definitions:
            if value is None:
                checks.append(dict(code=code, label=label, status='unknown', value=None, limit=limit))
                continue
            was_active = self.filters[code].active
            margin = self.settings['warning_deadband_deg']
            bad = value > limit if was_active else value > limit + margin
            active = self.filters[code].update(bad, now)
            if active and not was_active:
                self.observations[code] = self.observations.get(code, 0) + 1
            checks.append(dict(code=code, label=label, status='warn' if active else 'pending'
                               if value > limit else 'ok', value=round(value, 1), limit=limit))
            if active:
                feedback.append(dict(code=code, text=text))

        angle = m['elbow']
        before = self.counter.phase
        # Only substantial reversals across a real movement can create a range tip.
        # Near misses and one-off attempts are reserved for the rest summary.
        if self.last_angle is None:
            self.range_peak = self.range_valley = angle
        reversal = self.settings['partial_reversal_deg']
        margin = self.settings['partial_warning_margin_deg']
        if self.rising:
            self.range_peak = min(self.range_peak, angle)
            if angle > self.range_peak + reversal:
                if self.range_valley-self.range_peak >= 45 and self.up+margin < self.range_peak <= 125:
                    self.note('flexion', 'ลองงอศอกเพิ่มอีกนิดเท่าที่สบาย โดยไม่ยกต้นแขนตามนะ', now, deferred=True)
                self.last_top = self.range_peak
                self.rising = False
                self.range_valley = angle
        else:
            self.range_valley = max(self.range_valley, angle)
            if angle < self.range_valley - reversal:
                if (self.last_top is not None and self.last_top <= self.up
                    and self.range_valley-self.last_top >= 45 and self.range_valley < self.down-margin):
                    self.note('extension', 'ค่อย ๆ ลดแขนลงเพิ่มเท่าที่สบาย ไม่ต้องฝืนล็อกศอกนะ', now, deferred=True)
                self.rising = True
                self.range_peak = angle
        self.last_angle = angle
        if before == 'ready' and angle < self.counter.maximum - 12 and self.lift_start is None:
            self.lift_start = now
            self.minimum = angle
            self.cycle_issues = set()
        self.minimum = min(self.minimum, angle)
        if before == 'raised' and angle > self.minimum + 12 and self.lower_start is None:
            self.lower_start = now
        if self.lift_start is not None:
            self.cycle_issues.update(f['code'] for f in feedback)
            if self.notice and now < self.notice_until:
                if self.notice['code']!='range_option':self.cycle_issues.add(self.notice['code'])
        counted = self.counter.update(angle, now, self.down, self.up, self.settings['minimum_rep_excursion_deg'])
        if before == 'ready' and self.counter.phase == 'raised':
            self.lift_duration = now - self.lift_start if self.lift_start is not None else None
            scale = min(1, max(.5, (self.counter.maximum-angle) / max(45, self.preferred_down-self.preferred_up)))
            if self.lift_duration is not None and self.lift_duration < self.settings['minimum_lift_ms']*scale:
                self.cycle_issues.add('tempo')
                self.note('tempo', 'ลองผ่อนจังหวะตอนยกอีกนิด แล้วค่อย ๆ คุมแรงนะ', now)
        if counted:
            if 'curl_target_deg' in self.settings and self.minimum > self.preferred_up+5:
                self.note('range_option','นับให้แล้วนะ ถ้าควบคุมได้และอยากเพิ่มช่วงยก ลองลดมุมเป้าหมายทีละ 5 องศา ไม่ต้องฝืนนะ',now,deferred=True)
            lower_duration = now - self.lower_start if self.lower_start is not None else None
            scale = min(1, max(.5, (angle-self.minimum) / max(45, self.preferred_down-self.preferred_up)))
            if lower_duration is not None and lower_duration < self.settings['minimum_lower_ms']*scale:
                self.cycle_issues.add('tempo')
                self.note('tempo', 'ลองลดแขนช้าลงอีกนิด คุมแรงต้านตลอดทางนะ', now)
            if self.cycle_issues:
                self.flagged += 1
                labels = {'torso': 'ลำตัว', 'arm': 'ต้นแขน/ศอก', 'tempo': 'ความเร็ว',
                          'extension': 'ช่วงลด', 'flexion': 'ช่วงยก', 'range_option':'ช่วงยกที่ปรับได้'}
                self.last_rep = 'นับให้แล้วนะ · เซตถัดไปลองปรับ ' + ', '.join(labels[k] for k in sorted(self.cycle_issues))
            else:
                self.last_rep = 'นับแล้ว เก่งมาก · ค่อย ๆ ทำต่อได้เลย'
            self.lift_start = self.lower_start = None
            self.lift_duration = None
            self.minimum = 180
            self.cycle_issues = set()
        if self.notice and now < self.notice_until:
            feedback.append(self.notice)
        out.update(reps=self.counter.reps, flagged=self.flagged, last_rep=self.last_rep,
                   phase=self.counter.phase, calibrated=True, calibration=100, checks=checks,
                   metrics=dict(lean=round(lean, 1) if lean is not None else None, arm=round(arm, 1)), feedback=feedback,
                   form_level='warn' if feedback else 'ok',
                   observations=dict(self.observations),
                   form_title='ลองปรับอีกนิดนะ' if feedback else 'ทำต่อได้เลย ตามจังหวะที่สบาย',
                   message='นับแบบยืดหยุ่น พร้อมคำแนะนำเพื่อเซตถัดไป')
        return out
