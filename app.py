"""45 Fitness Coach v7: private browser cameras and independent workouts."""
import atexit
import copy
import hmac
import ipaddress
import json
import logging
import math
import os
import re
from pathlib import Path
import secrets
import socket
import threading
import time
import uuid

import numpy as np
from werkzeug.local import LocalProxy
from flask import g
from sessions import SessionRegistry, owned_profiles, owns, add_profile, migrate_legacy, rename_profile
import accounts
import recovery
import visitors

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from flask import Flask, Response, jsonify, redirect, render_template, request

from curl_counter import elbow_angle
from form_rules import FormCoach, measurements
import training_modes
import training_economy
import character
from grip import GripCoach, assess_grip
from leaderboard import LeaderboardStore
from voice import VoiceCache, PHRASES
from health import analyze as analyze_health
import membership
import shop
from exercises import CATALOG, EXERCISES, GROUPS
from motion_coach import MotionCoach, required_joints, pose_metrics
from planner import today_thailand

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / 'models' / 'pose_landmarker_lite.task'
SETTINGS = json.loads((ROOT / 'settings.json').read_text(encoding='utf-8-sig'))
GENTLE_COACH_VERSION = 30
store = LeaderboardStore(os.environ.get('FITNESS_DATA_PATH', str(ROOT / 'data' / 'fitness.db')))
voice_cache = VoiceCache(store.path.parent / 'voice-v13')
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
from share_access import load_key
ACCESS_KEY = load_key(store)
PUBLIC_URL = None
PUBLIC_HOST = '45-public.invalid'
STABLE_PUBLIC_URL=os.environ.get('FITNESS_PUBLIC_URL','').rstrip('/')
if STABLE_PUBLIC_URL:
    from urllib.parse import urlsplit
    parsed=urlsplit(STABLE_PUBLIC_URL)
    if parsed.scheme!='https' or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError('FITNESS_PUBLIC_URL must be an HTTPS origin such as https://fitness.example.com')
    PUBLIC_URL=STABLE_PUBLIC_URL
    PUBLIC_HOST=parsed.hostname.lower()
PHASES = {'waiting': 'รอแขนลง', 'ready': 'ยกแขนขึ้น', 'raised': 'ค่อย ๆ ลดแขน'}
ARM_IDS = {'left': (11, 13, 15), 'right': (12, 14, 16)}
ARM_LABELS = {'left': 'ซ้าย', 'right': 'ขวา'}
PAIRS = [(0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
         (9, 10), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
         (15, 17), (15, 19), (15, 21), (17, 19), (16, 18), (16, 20),
         (16, 22), (18, 20), (11, 23), (12, 24), (23, 24),
         (23,25),(24,26),(25,27),(26,28),(27,29),(28,30),(29,31),(30,32)]
logging.getLogger('werkzeug').setLevel(logging.WARNING)


def secret_matches(value):
    return hmac.compare_digest(value.encode('utf-8'), ACCESS_KEY.encode('ascii'))


def visible(point):
    return (point.visibility is not None and point.presence is not None
            and point.visibility >= .65 and point.presence >= .65
            and math.isfinite(point.x) and math.isfinite(point.y)
            and 0 <= point.x <= 1 and 0 <= point.y <= 1)


def lan_addresses():
    """List actual private adapter addresses. No requests to external services."""
    try:
        values = {item[4][0] for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}
        return sorted(ip for ip in values if ipaddress.ip_address(ip).is_private
                      and not ipaddress.ip_address(ip).is_loopback
                      and not ipaddress.ip_address(ip).is_link_local)
    except OSError:
        return []


def phone_links():
    return [dict(ip=ip, url=f'http://{ip}:5000/45-fitness-coach?key={ACCESS_KEY}') for ip in lan_addresses()]


def local_control():
    # A tunnel connects from loopback too. It must never inherit localhost's
    # access bypass. Start-Share.ps1 explicitly rewrites its origin Host.
    return (request.remote_addr in ('127.0.0.1','::1')
            and request.host.split(':')[0].lower() in ('127.0.0.1','localhost')
            and not any(request.headers.get(h) for h in
                        ('CF-Connecting-IP','X-Forwarded-For','X-Forwarded-Proto','Forwarded')))


def public_share_url():
    if STABLE_PUBLIC_URL:return STABLE_PUBLIC_URL+'/45-fitness-coach'
    return PUBLIC_URL+'/45-fitness-coach?key='+ACCESS_KEY if PUBLIC_URL else None


from strict_form import AttemptGate, geometry, MESSAGES as FORM_MESSAGES

class CameraCoach:
    def __init__(self, scoreboard=None):
        self.scoreboard = scoreboard or store
        self.condition = threading.Condition()
        self.stop_event = threading.Event()
        self.thread = None
        self.jpeg = None
        self.sequence = 0
        self.configure('right', SETTINGS['default_tolerance_deg'], 'arms')
        self.state = dict(running=False, exercise='curl', arm='right', focus='arms', camera=0,
                          message='เลือกชื่อผู้เล่นและแขน แล้วกดเปิดกล้อง', error=False,
                          paused=False, summary=None, profile=None, plan=None, plan_day=None, set_id=str(uuid.uuid4()))
        self.last_activity = None
        self.activity_angles = {}
        self.aggregate()

    def configure(self, arm, tolerance, focus, exercise='curl'):
        from angles import SetAngles
        self.angle_stats=SetAngles()
        self.exercise = exercise
        if hasattr(self,'grip_coach'):self.grip_coach=GripCoach()
        self.difficulty=getattr(self,'requested_difficulty','beginner')
        self.user_tolerance=tolerance
        cfg,effective=training_modes.options(exercise,self.difficulty,tolerance,SETTINGS,getattr(self,'curl_target',80))
        if getattr(self,'requested_auto_arm',False) and training_modes.supports_auto(exercise):arm='auto'
        self.selected_arm, self.focus = arm, focus
        self.active_arms = ['left', 'right'] if arm in ('both','auto') else [arm]
        self.arm_selector=training_modes.ArmSelector()
        self.auto_side='right'
        self.forms = {a: FormCoach(cfg,effective) if CATALOG[exercise]['family']=='curl' else MotionCoach(exercise,cfg,effective) for a in self.active_arms}
        self.outputs = {a: self.forms[a].base() for a in self.active_arms}
        self.smooth = {a: None for a in self.active_arms}
        self.last_good = {a: None for a in self.active_arms}
        self.rep_flags = {a: [] for a in self.active_arms}
        self.angle_sources = {a: None for a in self.active_arms}
        self.gates={a:AttemptGate() for a in self.active_arms}
        self.rep_events=[];self.attempt_serial=0;self.rejected=0;self.unverified=0;self.strict_notice=None

    def aggregate(self):
        auto=self.selected_arm=='auto'
        shown={self.auto_side:self.outputs[self.auto_side]} if auto else self.outputs
        outputs = list(shown.values())
        feedback, checks = [], []
        for arm, o in shown.items():
            for f in o['feedback']:
                feedback.append(dict(f, arm=arm, text=f'{ARM_LABELS[arm]}: {f["text"]}'))
            for c in o['checks']:
                checks.append(dict(c, arm=arm, label=f'{ARM_LABELS[arm]} · {c["label"]}'))
        both = self.selected_arm == 'both'
        reps = sum(o['reps'] for o in self.outputs.values()) if auto else min(o['reps'] for o in outputs) if both else outputs[0]['reps']
        flagged = sum(o['flagged'] for o in self.outputs.values()) if auto else sum(l or r for l, r in zip(self.rep_flags['left'], self.rep_flags['right'])) if both else outputs[0]['flagged']
        calibrated = all(o['calibrated'] for o in outputs)
        unknown = any(o['form_level'] == 'unknown' for o in outputs)
        warning = any(o['form_level'] == 'warn' for o in outputs)
        level = 'warn' if warning else 'unknown' if unknown else 'ok'
        last_rep = ('รอบล่าสุดที่ครบสองแขน: มีข้อสังเกต' if reps and
                    (self.rep_flags['left'][reps-1] or self.rep_flags['right'][reps-1]) else
                    'รอบล่าสุดที่ครบสองแขน: ไม่พบข้อเตือนในเกณฑ์ที่ตรวจ' if reps else
                    'รอให้แต่ละแขนทำครบหนึ่งรอบ') if both else outputs[0]['last_rep']
        phases = PHASES if CATALOG[self.exercise]['family']=='curl' else {
            'waiting':'จัดท่าเริ่มต้น','ready':'เริ่มการเคลื่อนไหว','raised':'ค่อย ๆ กลับท่าเริ่มต้น'}
        self.state.update(reps=reps, flagged=flagged, last_rep=last_rep, arms=copy.deepcopy(self.outputs),
                          calibrated=calibrated, calibration=min(o['calibration'] for o in outputs),
                          form_level=level, form_title='ลองปรับอีกนิดนะ' if warning else
                          'จัดแขนให้กล้องเห็นชัด' if unknown else 'ทำต่อได้เลย ตามจังหวะที่สบาย',
                          feedback=feedback, checks=checks, thresholds=outputs[0]['thresholds'],
                          phase=' · '.join(f'{ARM_LABELS[a]}: {phases[o["phase"]]}' for a, o in shown.items()),
                          angle=None if both else outputs[0]['angle'])

        self.state.update(difficulty=self.difficulty,auto_arm=auto,tracking_side=self.auto_side if auto else self.selected_arm,user_tolerance=self.user_tolerance)
        if auto:self.state['arm']='auto'
        self.state.update(rejected=self.rejected,unverified=self.unverified,rep_events=copy.deepcopy(self.rep_events),challenge=dict(remaining=self.challenge_remaining,target=20) if getattr(self,'challenge_id',None) else None)
        if self.strict_notice and time.monotonic()*1000<self.strict_notice['until']:
            f={k:v for k,v in self.strict_notice.items() if k!='until'}
            self.state['feedback'].insert(0,f);self.state['form_level']='warn';self.state['last_rep']=f['text']

    def snapshot(self):
        with self.condition:
            return copy.deepcopy(self.state)

    def reset_tracking(self, arm=None):
        for a in ([arm] if arm else self.active_arms):
            self.smooth[a] = self.last_good[a] = None
            if hasattr(self,'gates'):self.gates[a].lost()

    def start(self, arm, camera_index, tolerance, focus='arms', profile=None, exercise='curl', plan=None):
        with self.condition:
            if self.thread and self.thread.is_alive():
                return False
            if self.state.get('summary') and self.state['summary']['save_error']:
                self.pause()
                if self.state['summary']['save_error']:
                    return False
            self.stop_event.clear()
            self.configure(arm, tolerance, focus, exercise)
            self.jpeg = None
            self.state.update(running=True, exercise=exercise, arm=arm, focus=focus, camera=camera_index,
                              message='กำลังเปิดกล้องของคอม…', error=False, paused=False,
                              summary=None, profile=profile, plan=plan, plan_day=None, set_id=str(uuid.uuid4()))
            self.last_activity, self.activity_angles = None, {}
            self.aggregate()
            self.thread = threading.Thread(target=self.worker, args=(arm, camera_index), daemon=True)
            self.thread.start()
            return True

    def start_plan(self, profile, camera_index, tolerance):
        with self.condition:
            if self.state['running'] and (not self.state['paused'] or not self.state.get('plan')
                    or self.state['profile']['id']!=profile['id'] or self.stop_event.is_set()):
                raise ValueError('พักหรือปิดการเล่นเดิมก่อนเริ่มตารางของวันนี้')
            if self.state.get('summary') and self.state['summary']['save_error']:
                self.pause()
                if self.state['summary']['save_error']:
                    raise ValueError('บันทึกเซตเดิมยังไม่สำเร็จ ลองกดพักเซตอีกครั้ง')
            plan = self.scoreboard.next_plan(profile['id'])
            if not plan:
                day = self.scoreboard.plan_day(profile['id'])
                raise ValueError('ครบตารางวันนี้แล้ว ✓' if day['complete'] else 'วันนี้ยังไม่มีท่าในตาราง หรือเป็นวันพัก')
            exercise=plan['exercise']
            focus=CATALOG[exercise]['focus']
            if self.state['running']:
                self.configure(plan['arm_mode'],tolerance,focus,exercise)
                self.state.update(exercise=exercise,arm=plan['arm_mode'],focus=focus,plan=plan,plan_day=None)
                self.new_set()
                return True
            return self.start(plan['arm_mode'],camera_index,tolerance,focus,profile,exercise,plan)

    def stop(self):
        with self.condition:
            if self.state['running']:
                self.pause()
            self.stop_event.set()
            if self.state['running']:
                self.state['message'] = 'กำลังปิดกล้อง…'
            self.condition.notify_all()

    def reset(self):
        with self.condition:
            if self.state.get('plan'):
                return False
            summary = self.pause()
            if summary['save_error']:
                return False
            self.new_set()
            return True

    def new_set(self):
        """Condition must be held. Keep calibration; cancel unfinished cycles."""
        with self.condition:
            for a in self.active_arms:
                self.forms[a].reset()
                self.outputs[a] = self.forms[a].base()
                self.rep_flags[a] = []
            from angles import SetAngles
            self.angle_stats=SetAngles()
            self.reset_tracking()
            self.rep_events=[];self.attempt_serial=0;self.rejected=0;self.unverified=0;self.strict_notice=None
            self.last_activity, self.activity_angles = None, {}
            self.state.update(paused=False, summary=None, set_id=str(uuid.uuid4()))
            if getattr(self,'quality_enabled',False):
                from challenges import active_id,overview as challenge_overview
                profile=self.state.get('profile')
                self.challenge_id=active_id(self.scoreboard,profile['id']) if profile and self.exercise=='curl' else None
                run=challenge_overview(self.scoreboard,profile['id'])['run'] if self.challenge_id else None
                self.challenge_remaining=20-run['progress'] if run else 0
            self.aggregate()
            self.state['message'] = 'เริ่มเซตใหม่แล้ว ค่อย ๆ ยกตามจังหวะที่สบาย'

    def pause(self, automatic=False):
        with self.condition:
            self.state['paused'] = True
            observations = {}
            for arm, form in self.forms.items():
                for code, count in form.observations.items():
                    observations[code] = observations.get(code, 0) + count
            tips = {
                'arm': 'เซตถัดไปลองให้ศอกอยู่ข้างลำตัว และยกด้วยการงอศอกมากขึ้นนะ',
                'torso': 'ลองคุมลำตัวให้นิ่ง ถ้าต้องโยกช่วยยก ลองลดน้ำหนักที่ใช้ลงนะ',
                'tempo': 'ลองผ่อนจังหวะตอนยกและตอนลด ให้คุมแรงได้ตลอดทางนะ',
                'flexion': 'ลองงอศอกเพิ่มเท่าที่สบาย โดยไม่ยกต้นแขนตาม ไม่ต้องฝืนให้ถึงตัวเลขนะ',
                'extension': 'ลองลดแขนลงเพิ่มเท่าที่สบาย ไม่ต้องฝืนล็อกศอกนะ',
                'steady':'ลองคุมลำตัวให้นิ่งขึ้น ถ้าต้องเหวี่ยงช่วย ลองลดน้ำหนักนะ',
                'upper_still':'คุมต้นแขนให้นิ่ง แล้วขยับด้วยการงอและเหยียดศอกนะ',
                'soft_elbow':'รักษาศอกงอเล็กน้อยระหว่างยกแขน ไม่ต้องงอเข้าหาตัวมากนะ',
                'raise_height':'ยกประมาณระดับไหล่ก็พอ แล้วค่อย ๆ ลดกลับนะ',
                'grip_curl':'หงายฝ่ามือไปด้านหน้าและให้กล้องเห็นมือขณะลดแขน',
                'grip_hammer':'รักษาฝ่ามือเข้าหากันและนิ้วโป้งชี้ขึ้น',
                'wrist':'คุมข้อมือให้ต่อแนวปลายแขน ไม่พับช่วยยก',
                'range_option':'เริ่มเป้าหมาย 80 องศาได้ แล้วค่อยลดทีละ 5 องศาเมื่อควบคุมได้ ไม่ฝืน',
                'knee_bend':'ใน RDL ลองดันสะโพกไปหลังและผ่อนเข่าเล็กน้อย ไม่ย่อตัวเป็นสควอตนะ'}
            tips.update({'strict_'+code:pair[0] for code,pair in FORM_MESSAGES.items()})
            selected = [tips[c] for c in sorted(observations, key=observations.get, reverse=True) if c in tips][:3]
            if not selected:
                selected = ['ยังไม่พบข้อสังเกตที่ต่อเนื่องในสิ่งที่กล้องตรวจได้ คุมต้นแขนและจังหวะแบบนี้ต่อได้เลยนะ']
            if self.focus == 'arms':
                selected.append('โหมดนี้ดูแขนเป็นหลัก อย่าลืมคุมลำตัวและรักษาข้อมือตรงด้วยนะ')
            if CATALOG[self.exercise]['family']!='curl':
                if not observations:
                    selected = ['นับการเคลื่อนไหวแล้ว ลองทบทวนจุดสำคัญของท่านี้ก่อนเซตถัดไป']
                selected.append(CATALOG[self.exercise]['steps'][1])
            profile = self.state['profile']
            saved = False
            save_error = None
            credited = False
            if self.state['reps'] > 0 and profile:
                try:
                    extra = dict(plan=self.state['plan']) if self.state.get('plan') else {}
                    if getattr(self,'quality_enabled',False):extra['difficulty']=self.difficulty
                    result = self.scoreboard.save_set(self.state['set_id'], profile['id'], self.exercise, self.selected_arm,
                        self.state['reps'], self.state['flagged'],
                        self.forms['left'].counter.reps if 'left' in self.forms else 0,
                        self.forms['right'].counter.reps if 'right' in self.forms else 0, observations, **extra)
                    credited = bool(result.get('credited')) if isinstance(result,dict) else False
                    saved = True  # Existing set ID is also already safely saved.
                except Exception as error:
                    print(f'[SAVE ERROR] {error}', flush=True)
                    save_error = 'บันทึกอันดับไม่สำเร็จ ลองกดพักเซตอีกครั้ง'
            if profile and getattr(self,'quality_enabled',False) and not save_error:
                try:
                    from rewards import save_quality
                    save_quality(self.scoreboard,self.state['set_id'],profile['id'],self.exercise,self.selected_arm,self.state['reps'],self.rejected,self.unverified,accepted=sum(f.counter.reps for f in self.forms.values()))
                    training_economy.credit(self.scoreboard,self.state['set_id'],profile['id'],self.difficulty)
                    from challenges import credit
                    credit(self.scoreboard,getattr(self,'challenge_id',None),self.state['set_id'],profile['id'])
                    if getattr(self,'challenge_id',None):
                        from challenges import overview as challenge_overview
                        challenge_run=challenge_overview(self.scoreboard,profile['id'])['run']
                        if challenge_run and challenge_run['id']==self.challenge_id:
                            selected.insert(0,'ชาเลนจ์สำเร็จ รับ 1 เหรียญม่วงแล้ว 🎉' if challenge_run['complete'] else f"บันทึกชาเลนจ์แล้ว {challenge_run['progress']}/20 รอบ")
                except Exception:
                    save_error='บันทึกผลรอบและเหรียญไม่สำเร็จ กดพักอีกครั้งเพื่อลองใหม่'
            if getattr(self,'quality_enabled',False):
                selected.insert(0,f'รอบที่ต้องปรับและยังไม่นับ: {self.rejected} · ประเมินไม่ชัด: {self.unverified}')
            if profile and not save_error:
                try:
                    from angles import save as save_angles
                    save_angles(self.scoreboard,self.state['set_id'],profile['id'],self.exercise,self.angle_stats)
                except Exception:
                    logging.exception('Angle statistics save failed')
                    save_error='บันทึกมุมไม่สำเร็จ กดพักอีกครั้ง / Angle save failed; retry pause'
            plan_note = None
            if self.state.get('plan'):
                p = self.state['plan']
                plan_note = ('ครบเป้าหมายเซตนี้ บันทึกลงตารางแล้ว ✓' if credited else
                             'วันนี้เปลี่ยนวันแล้ว เริ่มตารางวันนี้ใหม่ได้' if p['date']!=today_thailand().isoformat() else
                             f'เซตนี้ได้ {self.state["reps"]}/{p["target_reps"]} ครั้ง ยังไม่ติ๊กเซต ลองใหม่เมื่อพร้อมนะ')
                try:
                    self.state['plan_day'] = self.scoreboard.plan_day(profile['id'],p['date'])
                except Exception:
                    self.state['plan_day'] = None
            self.state['summary'] = dict(set_id=self.state['set_id'], reps=self.state['reps'],
                flagged=self.state['flagged'], profile_name=profile['name'] if profile else 'ยังไม่ได้เลือกชื่อ',
                title=f'ทำได้ {self.state["reps"]} ครั้งแล้ว พักก่อนนะ', tips=selected,
                observations=observations, saved=saved, save_error=save_error, automatic=automatic,
                plan_credited=credited,plan_note=plan_note)
            self.state['message'] = save_error or 'พักเซตแล้ว ดูคำแนะนำ แล้วกดเริ่มเซตถัดไปเมื่อพร้อม'
            return copy.deepcopy(self.state['summary'])

    def resume(self):
        with self.condition:
            if not self.state['running'] or not self.state['paused']:
                return False
            if self.state.get('plan'):
                return self.start_plan(self.state['profile'],self.state['camera'],self.state['thresholds']['tolerance'])
            if self.state['summary'] and self.state['summary']['save_error']:
                self.pause()
                if self.state['summary']['save_error']:
                    return False
            self.new_set()
            return True

    def maybe_rest(self, now_ms):
        if getattr(self,'challenge_remaining',0)>0 and self.state['reps']>=self.challenge_remaining and not self.state['paused']:
            self.pause(automatic=True)
            return
        plan=self.state.get('plan')
        if plan and not self.state['paused'] and self.state['reps']>=plan['target_reps']:
            self.pause(automatic=True)
            return
        if (self.state['running'] and not self.state['paused'] and self.state['reps'] > 0
            and self.last_activity is not None and now_ms-self.last_activity >= SETTINGS['rest_timeout_ms']):
            self.pause(automatic=True)

    def recalibrate(self):
        with self.condition:
            for a in self.active_arms:
                self.forms[a].recalibrate()
                self.outputs[a] = self.forms[a].base()
            self.reset_tracking()
            self.aggregate()
            self.state['message'] = CATALOG[self.exercise]['setup']

    def draw(self, frame, landmarks):
        height, width = frame.shape[:2]
        def pixel(i):
            return round(landmarks[i].x * width), round(landmarks[i].y * height)
        allowed = set(range(33)) if self.focus == 'full' else set(range(25)) if self.focus == 'upper' else {11, 12}
        for a in self.active_arms:
            allowed.update(ARM_IDS[a])
            allowed.update((17, 19, 21) if a == 'left' else (18, 20, 22))
        for x, y in PAIRS:
            if x in allowed and y in allowed and visible(landmarks[x]) and visible(landmarks[y]):
                cv2.line(frame, pixel(x), pixel(y), (155, 125, 95), 2)
        for i in allowed:
            if visible(landmarks[i]):
                cv2.circle(frame, pixel(i), 3, (225, 182, 120), -1)
        for a in self.active_arms:
            ids = tuple(i+(0 if a=='left' else 1) for i in (23,25,27)) if self.focus=='full' else ARM_IDS[a]
            bad = {f['code'] for f in self.outputs[a]['feedback']}
            color = (80, 100, 255) if 'arm' in bad else (192, 230, 124)
            for x, y in zip(ids, ids[1:]):
                if visible(landmarks[x]) and visible(landmarks[y]):
                    cv2.line(frame, pixel(x), pixel(y), color, 5)
            for i in ids:
                if visible(landmarks[i]):
                    cv2.circle(frame, pixel(i), 7, color, -1)
            hip = 23 if a == 'left' else 24
            if self.focus == 'upper' and visible(landmarks[hip]) and visible(landmarks[ids[0]]):
                color = (80, 100, 255) if 'torso' in bad else (192, 230, 124)
                cv2.line(frame, pixel(ids[0]), pixel(hip), color, 4)

    def unavailable(self, now_ms, message):
        for a in self.active_arms:
            self.reset_tracking(a)
            self.outputs[a] = self.forms[a].unavailable(now_ms, message)
        self.aggregate()
        self.state['message'] = message

    def process(self, frame, result, ids_or_time, now_ms=None):
        # Four-argument form retained for existing test/tool compatibility.
        if now_ms is None:
            now_ms = ids_or_time
        height, width = frame.shape[:2]
        landmarks = result.pose_landmarks[0] if result.pose_landmarks else None
        world_poses = getattr(result, 'pose_world_landmarks', None)
        world = world_poses[0] if world_poses else None
        if self.state['paused']:
            if landmarks:
                self.draw(frame, landmarks)
            return
        if self.state.get('plan') and self.state['plan']['date']!=today_thailand().isoformat():
            self.pause(automatic=True)
            self.state['message']='เปลี่ยนวันแล้ว พักก่อนและเปิดตารางของวันนี้ใหม่'
            return
        if self.last_activity is None:
            self.last_activity = now_ms
        if not landmarks:
            self.unavailable(now_ms, 'ยังไม่เห็นคน — เพิ่มแสงและให้แขนอยู่ในภาพ')
            self.maybe_rest(now_ms)
            return
        if self.selected_arm=='auto':
            self.auto_side,switched=self.arm_selector.choose(landmarks,now_ms)
            if switched:
                # Keep per-side totals and calibration, cancel all unfinished cycles.
                for side in self.active_arms:
                    self.forms[side].reset_motion()
                    self.outputs[side]=self.forms[side].base()
                self.reset_tracking()
        for a in self.active_arms:
            if self.selected_arm=='auto' and a!=self.auto_side:continue
            ids = ARM_IDS[a]
            hip = 23 if a == 'left' else 24
            generic = CATALOG[self.exercise]['family']!='curl'
            needed = required_joints(self.exercise,a) if generic else (*ids, hip) if self.focus == 'upper' else ids
            form = self.forms[a]
            if not all(visible(landmarks[i]) for i in needed):
                self.reset_tracking(a)
                text = CATALOG[self.exercise]['camera'] if generic else 'ให้เห็นไหล่ ศอก ข้อมือ และสะโพก' if self.focus == 'upper' else 'ให้เห็นไหล่ ศอก ข้อมือครบ — ไม่จำเป็นต้องเห็นสะโพก'
                self.outputs[a] = form.unavailable(now_ms, text)
                continue
            points = [(landmarks[i].x * width, landmarks[i].y * height) for i in needed]
            raw, source = pose_metrics(self.exercise,a,landmarks,width,height,world) if generic or self.focus=='upper' else (measurements(*points),'2D')
            if raw is None:
                self.reset_tracking(a)
                self.outputs[a] = form.unavailable(now_ms, 'ปรับมุมให้เห็นต้นแขนและปลายแขนชัด')
                continue
            if not generic and source=='2D' and world and all(all(math.isfinite(v) for v in (world[i].x, world[i].y, world[i].z)) for i in ids):
                estimate = elbow_angle(*[(world[i].x, world[i].y, world[i].z) for i in ids])
                if estimate is not None:
                    raw['elbow'] = estimate
                    source = 'estimated_3D'
            if self.angle_sources[a] is not None and self.angle_sources[a] != source:
                form.recalibrate()
                self.reset_tracking(a)
            self.angle_sources[a] = source
            delta = now_ms - self.last_good[a] if self.last_good[a] is not None else 100
            alpha = 1 - math.exp(-delta / 70)
            previous = self.smooth[a]
            self.smooth[a] = raw if previous is None else {
                k: None if raw[k] is None else raw[k] if previous[k] is None
                else previous[k] + alpha * (raw[k] - previous[k]) for k in raw}
            self.last_good[a] = now_ms
            if a not in self.activity_angles or abs(self.smooth[a]['elbow']-self.activity_angles[a]) >= 8:
                self.activity_angles[a] = self.smooth[a]['elbow']
                self.last_activity = now_ms
            old_reps, old_flagged = form.counter.reps, form.flagged
            before_phase=form.counter.phase
            normalized=180-self.smooth[a]['elbow'] if generic and form.limits['increasing'] else self.smooth[a]['elbow']
            moving=before_phase=='raised' or before_phase=='ready' and normalized<form.counter.maximum-10
            self.angle_stats.sample(a,self.smooth[a],source,now_ms)
            self.outputs[a] = form.update(self.smooth[a], now_ms)
            if form.counter.reps>old_reps:self.angle_stats.completed(a,source)
            if getattr(self,'quality_enabled',False):
                known,bad=geometry(self.exercise,a,landmarks,world,self.smooth[a],self.difficulty)
                mapped={'arm':'upper_position','torso':'body_position','steady':'body_position','upper_still':'upper_still','soft_elbow':'elbow_shape','raise_height':'raise_height','knee_bend':'leg_position'}
                if CATALOG[self.exercise]['family']=='curl':
                    # Image-space arm/lean varies with camera rotation. For Curl,
                    # only the body-relative 3D check can reject those directions.
                    mapped.pop('arm');mapped.pop('torso')
                bad.extend(mapped[f['code']] for f in self.outputs[a]['feedback'] if f['code'] in mapped)
                grip=getattr(self,'grip_results',{}).get(a,{})
                if grip.get('blocked'):bad.append('grip')
                if any(f['code']=='wrist' for f in grip.get('feedback',[])):bad.append('wrist')
                active=self.gates[a].observe(known,bad,now_ms,moving or form.counter.phase=='raised')
                for code in active:
                    self.outputs[a]['feedback'].insert(0,dict(code='strict_'+code,text=FORM_MESSAGES[code][0]))
                self.outputs[a]['checks'].append(dict(label='แนวท่าและทิศทางแขน',status='warn' if active else 'pending' if not known else 'ok',value=None,limit=None,display='ลองปรับแนวท่า' if active else 'ยังประเมินทิศทางไม่ได้' if not known else 'กำลังติดตามแนวท่า'))
                if active:self.outputs[a]['form_level']='warn'
                if form.counter.reps>old_reps:
                    verdict,reasons=self.gates[a].finish()
                    self.attempt_serial+=1
                    self.rep_events.append(dict(id=self.attempt_serial,arm=a,result=verdict,reasons=reasons,difficulty=self.difficulty))
                    self.rep_events=self.rep_events[-24:]
                    if verdict!='accepted':
                        form.counter.reps=old_reps;form.flagged=old_flagged
                        if verdict=='rejected':self.rejected+=1
                        else:self.unverified+=1
                        code=reasons[0];text=('รอบนี้ยังไม่นับ · ' if verdict=='rejected' else 'รอประเมินก่อนนับ · ')+FORM_MESSAGES[code][0]
                        self.strict_notice=dict(code='strict_'+code,text=text,arm=a,until=now_ms+3500)
                        form.last_rep=text
                        self.outputs[a].update(reps=old_reps,flagged=old_flagged,last_rep=text,form_level='warn')
                        for reason in reasons:form.observations['strict_'+reason]=form.observations.get('strict_'+reason,0)+1
            self.outputs[a]['angle_source'] = source
            if form.counter.reps > old_reps:
                self.last_activity = now_ms
                self.rep_flags[a].append(form.flagged > old_flagged)
                print(f'[COUNT] {a}: {form.counter.reps}; flagged={form.flagged}', flush=True)
        self.aggregate()
        self.state['message'] = CATALOG[self.exercise]['camera']
        self.draw(frame, landmarks)
        self.maybe_rest(now_ms)

    def worker(self, arm, camera_index):
        capture = None
        started = time.monotonic()
        try:
            if not MODEL.is_file():
                raise RuntimeError('ไม่พบ models/pose_landmarker_lite.task')
            print(f'[START] Camera {camera_index}; arm={arm}; focus={self.focus}', flush=True)
            options = vision.PoseLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(MODEL)),
                running_mode=vision.RunningMode.VIDEO, num_poses=1,
                min_pose_detection_confidence=.6, min_pose_presence_confidence=.6,
                min_tracking_confidence=.6)
            with vision.PoseLandmarker.create_from_options(options) as detector:
                if self.stop_event.is_set():
                    return
                capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW) if os.name == 'nt' else cv2.VideoCapture(camera_index)
                if not capture.isOpened():
                    capture.release()
                    capture = cv2.VideoCapture(camera_index)
                if not capture.isOpened():
                    raise RuntimeError('เปิดกล้องไม่ได้ — ปิดโปรแกรมอื่นที่ใช้กล้อง หรือเปลี่ยนหมายเลขกล้อง')
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                previous_timestamp, failures = -1, 0
                while not self.stop_event.is_set():
                    ok, frame = capture.read()
                    if not ok:
                        failures += 1
                        with self.condition:
                            self.jpeg = None
                            self.unavailable(int((time.monotonic()-started)*1000), 'กล้องส่งภาพไม่สำเร็จ…')
                        if failures >= 10:
                            raise RuntimeError('กล้องส่งภาพไม่สำเร็จ — ลองปิดแล้วเปิดใหม่')
                        self.stop_event.wait(.1)
                        continue
                    failures = 0
                    timestamp = max(previous_timestamp + 1, int((time.monotonic()-started)*1000))
                    previous_timestamp = timestamp
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    result = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp)
                    with self.condition:
                        self.process(frame, result, timestamp)
                    frame = cv2.flip(frame, 1)
                    ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if ok:
                        with self.condition:
                            self.jpeg = encoded.tobytes()
                            self.sequence += 1
                            self.condition.notify_all()
                    self.stop_event.wait(.01)
        except Exception as error:
            print(f'[ERROR] {error}', flush=True)
            with self.condition:
                self.state.update(message=str(error), error=True)
        finally:
            if capture is not None:
                capture.release()
            with self.condition:
                if not self.state['paused']:
                    self.pause()
                for a in self.active_arms:
                    self.forms[a].recalibrate()
                    self.outputs[a] = self.forms[a].base()
                self.reset_tracking()
                self.aggregate()
                self.state['running'] = False
                self.jpeg = None
                if not self.state['error']:
                    self.state['message'] = 'ปิดกล้องแล้ว'
                self.condition.notify_all()
            print('[STOP] Camera released.', flush=True)

    def stream_frames(self):
        last_sequence = -1
        while True:
            with self.condition:
                self.condition.wait_for(lambda: not self.state['running'] or
                    (self.jpeg is not None and self.sequence != last_sequence), timeout=2)
                if not self.state['running']:
                    break
                if self.jpeg is None or self.sequence == last_sequence:
                    continue
                jpeg, last_sequence = self.jpeg, self.sequence
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n'


class BrowserCoach(CameraCoach):
    """One detector/counter per browser tab. No access to the host webcam."""
    def __init__(self, scoreboard=None):
        super().__init__(scoreboard)
        self.quality_enabled=True
        self.cardio=None
        self.detector = None
        self.hand_detector = None
        self.curl_target = 80
        self.grip_enabled = True
        self.grip_coach = GripCoach()
        self.grip_results = {}
        self.landmark_payload = []
        self.last_frame_at = time.monotonic()
        self.timestamp = -1

    def start(self, arm, camera_index, tolerance, focus='arms', profile=None, exercise='curl', plan=None):
        with self.condition:
            if self.state['running']:
                return False
            if self.state.get('summary') and self.state['summary']['save_error']:
                if self.pause()['save_error']:
                    return False
            options = vision.PoseLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(MODEL)),
                running_mode=vision.RunningMode.VIDEO, num_poses=1,
                min_pose_detection_confidence=.6, min_pose_presence_confidence=.6,
                min_tracking_confidence=.6)
            if self.detector is None:
                self.detector = vision.PoseLandmarker.create_from_options(options)
            self.cardio=None
            self.state.pop('cardio',None)
            self.grip_coach = GripCoach()
            self.grip_results = {}
            if CATALOG[exercise]['family']=='curl':
                focus='upper'
            self.configure(arm,tolerance,focus,exercise)
            self.stop_event.clear()
            self.last_frame_at = time.monotonic()
            self.frame_failures=0
            self.hand_disabled_until=0
            from challenges import active_id
            self.challenge_id=active_id(self.scoreboard,profile['id']) if profile and exercise=='curl' else None
            from challenges import overview as challenge_overview
            self.challenge_remaining=20-challenge_overview(self.scoreboard,profile['id'])['run']['progress'] if self.challenge_id else 0
            self.last_activity, self.activity_angles = None, {}
            self.state.update(running=True, exercise=exercise, arm=arm, focus=focus, camera=camera_index,
                message='กล้องของคุณพร้อมแล้ว จัดท่าเริ่มต้น', error=False, paused=False,
                summary=None, profile=profile, plan=plan, plan_day=None, set_id=str(uuid.uuid4()))
            self.aggregate()
            return True

    def stop(self):
        with self.condition:
            if self.state['running']:
                self.pause()
            self.state.update(running=False, message='ปิดกล้องของคุณแล้ว')
            self.stop_event.set()
            self.jpeg = None

    def snapshot(self):
        with self.condition:
            if self.cardio:self.state['cardio']=self.cardio.snapshot()
            return super().snapshot()

    def pause(self, automatic=False):
        if self.cardio:
            with self.condition:
                self.cardio.stop()
                summary=dict(save_error=None,saved=self.cardio.saved,reps=0,observations={})
                self.state.update(paused=True,summary=summary)
                return summary
        return super().pause(automatic)

    def release_detector(self):
        with self.condition:
            for name in ('detector','hand_detector'):
                detector=getattr(self,name,None)
                setattr(self,name,None)
                if detector is not None:
                    try:detector.close()
                    except Exception:logging.exception('Camera detector cleanup: %s',name)
            self.timestamp = -1

    def accept_frame(self, frame, set_id, landmarks_only=False):
        with self.condition:
            if not self.state['running'] or self.detector is None or set_id != self.state['set_id']:
                raise ValueError('เซตเปลี่ยนหรือปิดกล้องแล้ว')
            now=time.monotonic()
            # A network pause cancels the incomplete repetition, not the neutral
            # calibration. Otherwise >2 s round trips restart preparation forever.
            gap = now-self.last_frame_at
            if gap > 10:
                self.recalibrate()
            elif gap > 2:
                for side in self.active_arms:
                    self.forms[side].reset_motion()
                self.reset_tracking()
            self.last_frame_at=now
            timestamp=max(self.timestamp+1,int(now*1000))
            self.timestamp=timestamp
            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            result=self.detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb),timestamp)
            poses=result.pose_landmarks[0] if result.pose_landmarks else None
            world=result.pose_world_landmarks[0] if result.pose_world_landmarks else None
            if self.cardio:
                self.state['cardio']=self.cardio.update(poses,frame.shape[1]/frame.shape[0],world=world)
                self.state['focus']='upper' if self.cardio.mode=='upper' else 'full'
                points=[[round(p.x,4),round(p.y,4),round(p.visibility or 0,3)] for p in poses] if poses else []
                return dict(landmarks=points,hands=[],state=self.snapshot(),server_today=today_thailand().isoformat())
            previous_grip=self.grip_results
            self.grip_results={}
            hand_points=[]
            if self.grip_enabled and CATALOG[self.exercise]['family']=='curl' and now>=getattr(self,'hand_disabled_until',0):
                try:
                    if self.hand_detector is None:
                        self.hand_detector=mp.solutions.hands.Hands(static_image_mode=False,max_num_hands=2,model_complexity=0,min_detection_confidence=.65,min_tracking_confidence=.65)
                    hands=self.hand_detector.process(rgb)
                    hand_points=[[[round(p.x,4),round(p.y,4)] for p in hand.landmark]
                                 for hand in (hands.multi_hand_landmarks or [])]
                    for side in self.active_arms:
                        raw=assess_grip(side,poses,world,hands,frame.shape[1],frame.shape[0])
                        self.grip_results[side]=self.grip_coach.update(side,self.exercise,raw,timestamp)
                except Exception:
                    logging.exception('Hand tracker unavailable; retaining body camera and retrying in 30 seconds')
                    self.grip_results={};hand_points=[];self.hand_disabled_until=now+30
                    if self.hand_detector is not None:
                        try:self.hand_detector.close()
                        except Exception:pass
                        self.hand_detector=None
            self.process(frame,result,timestamp)
            if CATALOG[self.exercise]['family']=='curl':
                for side in self.active_arms:
                    shoulder=self.grip_coach.shoulders(side,poses,frame.shape[1],frame.shape[0],timestamp)
                    if shoulder:
                        self.outputs[side]['checks'].append(shoulder)
                        if shoulder['status']=='warn':
                            self.outputs[side]['feedback'].append(dict(code='shoulders',text='ลองวางไหล่ให้สมดุล ไม่เอียงตัวช่วยยกนะ'))
                            self.outputs[side]['form_level']='warn'
            for side,grip in self.grip_results.items():
                out=self.outputs[side]
                out['checks'].extend(grip['checks'])
                out['feedback'].extend(grip['feedback'])
                out['grip_verified']=grip['verified']
                previous_codes={f['code'] for f in previous_grip.get(side,{}).get('feedback',[])}
                for f in grip['feedback']:
                    if f['code'] not in previous_codes:
                        self.forms[side].observations[f['code']]=self.forms[side].observations.get(f['code'],0)+1
                if grip['feedback']:out['form_level']='warn'
            self.aggregate()
            self.state['curl_target']=self.curl_target
            self.state['grip_enabled']=self.grip_enabled
            self.landmark_payload=[[round(p.x,4),round(p.y,4),round(p.visibility or 0,3)] for p in poses] if poses else []
            if landmarks_only:
                return dict(landmarks=self.landmark_payload,hands=hand_points,state=self.snapshot(),server_today=today_thailand().isoformat())
            ok,encoded=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,75])
            if not ok:
                raise ValueError('แปลงภาพไม่สำเร็จ')
            return encoded.tobytes()


sessions = SessionRegistry(lambda: BrowserCoach(store))
coach = LocalProxy(lambda: g.coach_session['coach'])
atexit.register(sessions.stop_all)


def cleanup_sessions():
    while True:
        time.sleep(5)
        sessions.sweep()


threading.Thread(target=cleanup_sessions,daemon=True).start()


@app.before_request
def authorize():
    origin = request.headers.get('Origin')
    public_request = request.host.split(':')[0].lower()==PUBLIC_HOST
    expected_origin = PUBLIC_URL if public_request else request.host_url.rstrip('/')
    if request.method == 'POST' and origin and origin.rstrip('/') != expected_origin:
        return jsonify(error='เปิดคำสั่งจากหน้าเว็บนี้เท่านั้น'), 403
    if local_control():
        return None
    if STABLE_PUBLIC_URL and public_request:
        return None
    if request.path in ('/', '/45-fitness-coach') and secret_matches(request.args.get('key', '')):
        response = redirect('/45-fitness-coach')
        response.set_cookie('coach_access', ACCESS_KEY, httponly=True, samesite='Strict',
                            secure=public_request or request.is_secure)
        return response
    if not secret_matches(request.cookies.get('coach_access', '')):
        return 'เปิดด้วยลิงก์หรือ QR จากหน้าเว็บบนคอมที่รัน 45 Fitness Coach', 403


@app.before_request
def private_session():
    protected = request.path in ('/start','/stop','/reset','/pause','/resume','/calibrate','/frame',
        '/camera/auto-arm','/profiles','/plans/today/start','/health/analyze','/camera/recover') or request.path.startswith(('/profiles/','/vip','/admin/','/social/','/cardio/'))
    token=request.headers.get('X-Coach-Session','')
    if request.path == '/status' and token:
        protected=True
    if not protected:
        return None
    item=sessions.get(token)
    account=accounts.lookup(store,request.cookies.get(accounts.COOKIE,''))
    guest_owner=visitors.owner(request.cookies.get(visitors.COOKIE,''))
    valid_account=bool(item and account and account['owner']==item['owner'] and item.get('login_hash')==accounts.digest(request.cookies.get(accounts.COOKIE,'')))
    valid_guest=bool(item and not account and guest_owner and item['owner']==guest_owner)
    if not (valid_account or valid_guest):
        return jsonify(error='เซสชันหมดอายุ กรุณารีเฟรชหน้าเว็บ',session_expired=True),401
    g.coach_session=item
    g.account=account
    match=re.match(r'^/profiles/(\d+)(?:/|$)',request.path)
    data=request.get_json(silent=True) if request.is_json else None
    profile_id=int(match.group(1)) if match else data.get('profile_id') if isinstance(data,dict) else None
    if profile_id is not None:
        if type(profile_id) is not int:
            return jsonify(error='เลือกชื่อผู้เล่นให้ถูกต้อง'),400
        if not owns(store,item['owner'],profile_id):
            return jsonify(error='ไม่พบข้อมูลผู้เล่นของคุณ'),404


@app.before_request
def vip_guard():
    if request.method!='POST' or request.path not in ('/start','/plans/today/start','/resume','/reset'):
        return None
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict):return None
    sessions.lock.acquire()
    g.control_locked=True
    state=coach.snapshot()
    exercise=data.get('exercise','curl') if request.path=='/start' else state.get('exercise')
    if request.path=='/plans/today/start' or request.path=='/resume' and state.get('plan'):
        pid=data.get('profile_id') if request.path=='/plans/today/start' else (state.get('profile') or {}).get('id')
        if type(pid) is int and owns(store,g.coach_session['owner'],pid):
            plan=store.next_plan(pid)
            exercise=plan['exercise'] if plan else None
    if isinstance(exercise,str) and exercise in membership.LOCKED and not membership.active(store,g.coach_session['owner']):
        return jsonify(error='ท่านี้สำหรับ VIP Home / VIP Home exercise',vip_required=True),403


@app.before_request
def control_guard():
    if request.method!='POST' or request.path not in ('/start','/plans/today/start','/cardio/start') and not re.fullmatch(r'/profiles/\d+/calendar/(week|day)',request.path):
        return None
    if not getattr(g,'control_locked',False):
        sessions.lock.acquire()
        g.control_locked=True
    data=request.get_json(silent=True)
    match=re.match(r'/profiles/(\d+)/',request.path)
    profile_id=int(match.group(1)) if match else data.get('profile_id') if isinstance(data,dict) else None
    if profile_id is None:
        return None
    current=g.coach_session['coach']
    active=0
    for item in sessions.items.values():
        other=item['coach']
        state=other.snapshot()
        if state['running']:
            active+=1
            if other is not current and state.get('profile') and state['profile']['id']==profile_id:
                return jsonify(error='ชื่อนี้กำลังเล่นในอีกหน้าเว็บ ปิดกล้องหน้านั้นก่อน หรือเลือกชื่ออื่น'),409
    if request.path in ('/start','/plans/today/start','/cardio/start') and not current.state['running'] and active>=8:
        return jsonify(error='ขณะนี้มีกล้องใช้งาน 8 เครื่อง รอให้คนหนึ่งปิดกล้องก่อน'),503


@app.teardown_request
def release_control(error=None):
    if getattr(g,'control_locked',False):
        g.control_locked=False
        sessions.lock.release()


auth_attempts={}
auth_lock=threading.Lock()


def auth_limited():
    address=request.headers.get('CF-Connecting-IP') if request.host.split(':')[0].lower()==PUBLIC_HOST else request.remote_addr
    now=time.monotonic()
    with auth_lock:
        for key in list(auth_attempts):
            auth_attempts[key]=[t for t in auth_attempts[key] if now-t<60]
            if not auth_attempts[key]:
                del auth_attempts[key]
        attempts=auth_attempts.setdefault(address,[])
        if len(attempts)>=15:
            return True
        attempts.append(now)
    return False


def login_response(account):
    token=accounts.issue(store,account)
    response=jsonify(ok=True,email=account['email'])
    response.set_cookie(accounts.COOKIE,token,max_age=accounts.LIFETIME,httponly=True,samesite='Strict',
        secure=request.is_secure or request.host.split(':')[0].lower()==PUBLIC_HOST)
    return response


@app.post('/auth/register')
def register_account():
    if auth_limited():
        return jsonify(error='ลองหลายครั้งเกินไป กรุณารอ 1 นาที'),429
    try:
        data=request.get_json(silent=True)
        recovery.number(data.get('recovery_number') if isinstance(data,dict) else None)
        account=accounts.register(store,data)
        recovery.save(store,account['id'],data['recovery_number'])
        with sessions.lock:
            guest=visitors.owner(request.cookies.get(visitors.COOKIE,''))
            for item in sessions.items.values():
                if item['owner']==guest:item['coach'].stop()
            visitors.adopt(store,request.cookies.get(visitors.COOKIE,''),account)
        return login_response(account)
    except ValueError as error:
        return jsonify(error=str(error)),400


@app.post('/auth/login')
def login_account():
    if auth_limited():
        return jsonify(error='ลองหลายครั้งเกินไป กรุณารอ 1 นาที'),429
    try:
        return login_response(accounts.login(store,request.get_json(silent=True)))
    except ValueError as error:
        return jsonify(error=str(error)),400


@app.get('/auth/me')
def whoami():
    account=accounts.lookup(store,request.cookies.get(accounts.COOKIE,''))
    return jsonify(email=account['email'],recovery_ready=recovery.has_number(store,account['id'])) if account else jsonify(guest=True)


@app.post('/auth/recovery/verify')
def verify_recovery():
    if auth_limited():return jsonify(error='รอ 1 นาที / Wait one minute'),429
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict):return jsonify(error='Invalid request'),400
    address=request.headers.get('CF-Connecting-IP') if request.host.split(':')[0].lower()==PUBLIC_HOST else request.remote_addr
    try:
        accounts.schema(store)
        from password_mail import request_reset
        request_reset(store,data.get('email'),address,public_share_url())
        return jsonify(ok=True,message='หากมีบัญชีนี้ ระบบจะส่งลิงก์รีเซ็ตไปยังอีเมล กรุณาตรวจกล่องจดหมายและสแปม / If registered, a reset link will be emailed. Check inbox and spam.')
    except ValueError as error:return jsonify(error=str(error)),400


@app.post('/auth/recovery/reset')
def reset_recovery():
    if auth_limited():return jsonify(error='รอ 1 นาที / Wait one minute'),429
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict):return jsonify(error='Invalid request'),400
    try:
        with sessions.lock:
            owner=recovery.reset(store,data.get('ticket'),data.get('password'))
            for item in sessions.items.values():
                if item['owner']==owner:item['coach'].stop()
        return jsonify(ok=True)
    except ValueError as error:return jsonify(error=str(error)),400


@app.post('/auth/recovery/setup')
def setup_recovery():
    if auth_limited():return jsonify(error='รอ 1 นาที / Wait one minute'),429
    account=accounts.lookup(store,request.cookies.get(accounts.COOKIE,''))
    if not account:return jsonify(error='เข้าสู่ระบบก่อน / Sign in first'),401
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict):return jsonify(error='Invalid request'),400
    try:
        accounts.login(store,dict(email=account['email'],password=data.get('password')))
        recovery.save(store,account['id'],data.get('recovery_number'))
        return jsonify(ok=True)
    except ValueError as error:return jsonify(error=str(error)),400


@app.post('/auth/logout')
def logout_account():
    token=request.cookies.get(accounts.COOKIE,'')
    hashed=accounts.digest(token)
    with sessions.lock:
        for item in sessions.items.values():
            if item.get('login_hash')==hashed:
                item['coach'].stop()
    accounts.revoke(store,token)
    response=jsonify(ok=True)
    response.delete_cookie(accounts.COOKIE,secure=request.is_secure or request.host.split(':')[0].lower()==PUBLIC_HOST,samesite='Strict')
    return response


@app.post('/session')
def new_session():
    account=accounts.lookup(store,request.cookies.get(accounts.COOKIE,''))
    guest=request.cookies.get(visitors.COOKIE,'')
    if not visitors.valid(guest):guest=secrets.token_urlsafe(32)
    owner=account['owner'] if account else visitors.owner(guest)
    if account and local_control():
        migrate_legacy(store,account['owner'])
    try:
        token=sessions.create(owner)
        if account:sessions.items[token]['login_hash']=accounts.digest(request.cookies.get(accounts.COOKIE,''))
        data=request.get_json(silent=True) or {}
        default_profile=visitors.ensure_profile(store,owner) if not account or isinstance(data,dict) and data.get('auto_profile') else None
    except ValueError as error:
        return jsonify(error=str(error)),503
    response=jsonify(session_token=token,email=account['email'] if account else None,guest=not bool(account),default_profile=default_profile,version=GENTLE_COACH_VERSION)
    if not account:response.set_cookie(visitors.COOKIE,guest,max_age=accounts.LIFETIME,httponly=True,samesite='Strict',secure=request.is_secure or request.host.split(':')[0].lower()==PUBLIC_HOST)
    return response


@app.after_request
def private_headers(response):
    if not request.path.startswith('/static/') and not request.path.startswith('/speech/'):
        response.headers['Cache-Control']='no-store'
    if request.path.startswith('/static/'):
        response.headers['Cache-Control']='no-cache, must-revalidate'
    response.headers['Referrer-Policy']='no-referrer'
    if request.path not in ('/','/45-fitness-coach','/robots.txt','/sitemap.xml') and not request.path.startswith('/static/'):
        response.headers['X-Robots-Tag']='noindex, nofollow'
    return response


@app.get('/')
@app.get('/45-fitness-coach')
def index():
    return render_template('index.html', settings=SETTINGS, voice_config=voice_cache.configuration(),
                           public_url=STABLE_PUBLIC_URL,exercises=EXERCISES,groups=GROUPS,server_today=today_thailand().isoformat())


@app.get('/robots.txt')
def robots():
    text='User-agent: *\nDisallow: /\n'
    if STABLE_PUBLIC_URL:
        text='User-agent: *\nAllow: /$\nAllow: /45-fitness-coach$\nAllow: /static/\nDisallow: /\nSitemap: '+STABLE_PUBLIC_URL+'/sitemap.xml\n'
    return Response(text,mimetype='text/plain')


@app.get('/sitemap.xml')
def sitemap():
    from xml.sax.saxutils import escape
    if not STABLE_PUBLIC_URL:return Response('',status=404)
    return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'+escape(STABLE_PUBLIC_URL)+'/45-fitness-coach</loc></url></urlset>',mimetype='application/xml')


@app.get('/connection')
def connection():
    return jsonify(links=phone_links(),name='45 Fitness Coach',camera_source='browser',
                   share_url=public_share_url(),local_admin=local_control())


@app.post('/share/register')
def register_share():
    global PUBLIC_URL
    if not local_control():
        return jsonify(error='เปิดหรือปิดลิงก์แชร์จาก PowerShell บนคอมเท่านั้น'),403
    if STABLE_PUBLIC_URL:return jsonify(error='Permanent domain is configured; temporary sharing is disabled'),409
    data=request.get_json(silent=True)
    if not isinstance(data,dict):
        return jsonify(error='ข้อมูลลิงก์ไม่ถูกต้อง'),400
    url=data.get('base_url')
    if url is not None and (not isinstance(url,str) or not re.fullmatch(r'https://[a-z0-9-]+\.trycloudflare\.com',url)):
        return jsonify(error='ใช้ HTTPS Quick Tunnel ที่สร้างจากสคริปต์เท่านั้น'),400
    PUBLIC_URL=url
    return jsonify(ok=True,share_url=public_share_url())


@app.get('/share/qr')
def share_qr():
    url=public_share_url()
    if not url:
        return 'Sharing is not running',404
    qr=cv2.QRCodeEncoder_create().encode(url)
    qr=cv2.copyMakeBorder(qr,8,8,8,8,cv2.BORDER_CONSTANT,value=255)
    # Keep each QR module an equal integer number of pixels; fractional scaling
    # can create uneven cells that some scanners cannot decode.
    scale=max(1,round(480/qr.shape[0]))
    qr=cv2.resize(qr,None,fx=scale,fy=scale,interpolation=cv2.INTER_NEAREST)
    ok,encoded=cv2.imencode('.png',qr)
    return Response(encoded.tobytes(),mimetype='image/png',headers={'Cache-Control':'no-store'}) if ok else ('QR unavailable',500)


@app.get('/connection-qr/<int:number>')
def connection_qr(number):
    links = phone_links()
    if not 0 <= number < len(links):
        return 'No LAN address', 404
    qr = cv2.QRCodeEncoder_create().encode(links[number]['url'])
    qr = cv2.copyMakeBorder(qr, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=255)
    scale = max(1, round(420 / qr.shape[0]))
    qr = cv2.resize(qr, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    ok, encoded = cv2.imencode('.png', qr)
    if not ok:
        return 'QR unavailable', 500
    return Response(encoded.tobytes(), mimetype='image/png', headers={'Cache-Control':'no-store'})


@app.get('/status')
def status():
    if not request.headers.get('X-Coach-Session'):
        return jsonify(ok=True,version=GENTLE_COACH_VERSION,camera_source='browser')
    return jsonify(dict(coach.snapshot(),server_today=today_thailand().isoformat()))


def apply_coach_options(data):
    level=data.get('difficulty','beginner');auto=data.get('auto_arm',False)
    if level not in training_modes.LEVELS or type(auto) is not bool:return jsonify(error='Invalid training mode / โหมดไม่ถูกต้อง'),400
    if request.path=='/plans/today/start' and auto:return jsonify(error='ตารางใช้ข้างตามแผน / Planned sets use their prescribed side'),400
    if request.path=='/start' and auto and not training_modes.supports_auto(data.get('exercise','curl')):return jsonify(error='Auto arms is for upper-body exercises / สลับแขนอัตโนมัติใช้กับท่าช่วงบน'),400
    if coach.state['running'] and not (request.path=='/plans/today/start' and coach.state['paused'] and coach.state.get('plan')):return jsonify(error='Stop the current set before changing training mode / ปิดเซตก่อนเปลี่ยนโหมด'),409
    coach.requested_difficulty=level;coach.requested_auto_arm=auto
    target=data.get('curl_target',80)
    grip=data.get('grip_enabled',True)
    if type(target) is not int or not 40<=target<=100 or type(grip) is not bool:
        return jsonify(error='มุมเป้าหมายต้องอยู่ระหว่าง 40–100 องศา'),400
    if isinstance(coach._get_current_object() if hasattr(coach,'_get_current_object') else coach,BrowserCoach):
        coach.curl_target=target
        coach.grip_enabled=grip
    return None


@app.post('/start')
def start():
    if request.headers.get('X-Set-ID') and request.headers['X-Set-ID']!=coach.state['set_id']:
        return jsonify(error='Cancelled camera operation'),409
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify(error='รูปแบบคำสั่งไม่ถูกต้อง'), 400
    arm, camera = data.get('arm', 'right'), data.get('camera', 0)
    tolerance = data.get('tolerance', SETTINGS['default_tolerance_deg'])
    focus = data.get('focus', 'arms')
    exercise=data.get('exercise','curl')
    if not isinstance(exercise,str) or exercise not in CATALOG:
        return jsonify(error='เลือกท่าจากรายการที่เปิดใช้งาน'), 400
    if type(tolerance) is not int or not 5 <= tolerance <= 50:
        return jsonify(error='ความเผื่อต้องเป็นจำนวนเต็ม 5–50 องศา'), 400
    if arm not in CATALOG[exercise]['modes'] or type(camera) is not int or not 0 <= camera <= 5 or focus not in ('arms', 'upper','full'):
        return jsonify(error='ค่าแขน กล้อง หรือโหมดไม่ถูกต้อง'), 400
    profile_id = data.get('profile_id')
    if profile_id is not None and type(profile_id) is not int:
        return jsonify(error='เลือกชื่อผู้เล่นให้ถูกต้อง'), 400
    profile = store.profile(profile_id) if profile_id is not None else None
    if not profile:
        return jsonify(error='ไม่พบชื่อผู้เล่น กรุณาเลือกหรือสร้างชื่อก่อน'), 400
    error=apply_coach_options(data)
    if error:return error
    if CATALOG[exercise]['family']!='curl':
        focus=CATALOG[exercise]['focus']
    elif focus=='full':
        focus='upper'
    try:
        started=coach.start(arm,camera,tolerance,focus,profile) if exercise=='curl' else coach.start(arm,camera,tolerance,focus,profile,exercise)
    except Exception:
        logging.exception('Camera initialization failed')
        return jsonify(error='เปิดระบบตรวจท่าไม่สำเร็จ กดรีเซ็ตกล้อง หากยังไม่ได้ดูข้อผิดพลาดใน PowerShell'),503
    if not started:
        return jsonify(error='กล้องยังทำงานหรือกำลังปิด — รอสักครู่'), 409
    print('[CAMERA] Workout started',flush=True)
    return jsonify(ok=True,state=coach.snapshot())


@app.post('/stop')
def stop():
    with coach.condition:
        expected=request.headers.get('X-Set-ID')
        if expected and expected!=coach.state['set_id']:
            return jsonify(error='Ignored stop from an older workout'),409
        coach.stop()
    print('[CAMERA] Workout stopped',flush=True)
    return jsonify(ok=True,state=coach.snapshot())


@app.post('/camera/recover')
def recover_camera():
    with sessions.lock:
        old=g.coach_session['coach']
        with old.condition:
            if request.headers.get('X-Set-ID')!=old.state['set_id']:
                return jsonify(error='สถานะกล้องเปลี่ยนแล้ว กดรีเซ็ตอีกครั้ง / Camera state changed; retry'),409
            old.stop()
            if (old.state.get('summary') or {}).get('save_error'):
                return jsonify(error='บันทึกเซตไม่สำเร็จ กรุณาลองใหม่ก่อนรีเซ็ต / Save failed; retry before resetting'),409
            data=request.get_json(silent=True) or {}
            if isinstance(data,dict) and data.get('rebuild') is True:old.release_detector()
            fresh=old
            fresh.state['set_id']=str(uuid.uuid4())
    print('[CAMERA] Session reset; ready for a fresh stream',flush=True)
    return jsonify(ok=True,state=fresh.snapshot())


@app.post('/local/cameras/reset')
def local_reset_cameras():
    if not local_control():return jsonify(error='Local computer only'),403
    reset=0
    failed=0
    with sessions.lock:
        for item in sessions.items.values():
            old=item['coach']
            with old.condition:
                old.stop()
                if (old.state.get('summary') or {}).get('save_error'):
                    failed+=1
                    continue
                old.release_detector()
                old.state['set_id']=str(uuid.uuid4())
                reset+=1
    if failed:return jsonify(error='Some sets could not be saved. Retry before stopping the server.',reset_sessions=reset,failed_sessions=failed),409
    return jsonify(ok=True,reset_sessions=reset)


@app.post('/reset')
def reset():
    if not coach.reset():
        return jsonify(error='ขณะเล่นตามตารางให้ใช้ปุ่มเซตถัดไป; หากบันทึกไม่สำเร็จ กดพักเซตเพื่อลองอีกครั้ง'), 409
    return jsonify(ok=True,state=coach.snapshot())


@app.post('/pause')
def pause():
    summary=coach.pause()
    return jsonify(ok=True,summary=summary,state=coach.snapshot())


@app.post('/resume')
def resume():
    try:
        resumed=coach.resume()
    except ValueError as error:
        return jsonify(error=str(error)),409
    if not resumed:
        return jsonify(error='เปิดกล้องและพักเซตก่อน หรือแก้ปัญหาบันทึกคะแนนก่อนเริ่มใหม่'), 409
    return jsonify(ok=True,state=coach.snapshot())


@app.get('/profiles/<int:profile_id>/calendar')
def calendar_month(profile_id):
    try:
        return jsonify(store.plan_month(profile_id,request.args.get('month',today_thailand().strftime('%Y-%m'))))
    except ValueError as error:
        return jsonify(error=str(error)),400


def active_plan_date(profile_id):
    state=coach.snapshot()
    plan=state.get('plan')
    return plan['date'] if state['running'] and plan and plan['profile_id']==profile_id else None


@app.post('/profiles/<int:profile_id>/calendar/week')
def upload_calendar(profile_id):
    try:
        with coach.condition:
            result=store.upload_week(profile_id,request.get_json(silent=True),active_plan_date(profile_id))
        return jsonify(ok=True,**result)
    except ValueError as error:
        return jsonify(error=str(error)),400


@app.post('/profiles/<int:profile_id>/calendar/day')
def update_calendar_day(profile_id):
    data=request.get_json(silent=True)
    if not isinstance(data,dict):
        return jsonify(error='รูปแบบตารางไม่ถูกต้อง'),400
    try:
        with coach.condition:
            day=store.save_plan_day(profile_id,data.get('date'),data.get('items'),active_plan_date(profile_id),data.get('adjust_remaining') is True)
        return jsonify(day=day)
    except ValueError as error:
        return jsonify(error=str(error)),400


@app.post('/plans/today/start')
def start_today_plan():
    if request.headers.get('X-Set-ID') and request.headers['X-Set-ID']!=coach.state['set_id']:
        return jsonify(error='Cancelled camera operation'),409
    data=request.get_json(silent=True)
    if not isinstance(data,dict):
        return jsonify(error='เลือกผู้เล่นก่อนเริ่มตาราง'),400
    profile_id,camera,tolerance=data.get('profile_id'),data.get('camera',0),data.get('tolerance',10)
    if type(profile_id) is not int or type(camera) is not int or not 0<=camera<=5 or type(tolerance) is not int or not 5<=tolerance<=50:
        return jsonify(error='ค่าผู้เล่น กล้อง หรือความเผื่อไม่ถูกต้อง'),400
    profile=store.profile(profile_id)
    if not profile:
        return jsonify(error='ไม่พบชื่อผู้เล่น'),400
    error=apply_coach_options(data)
    if error:return error
    try:
        if not coach.start_plan(profile,camera,tolerance):
            return jsonify(error='กล้องกำลังปิด รอสักครู่แล้วลองใหม่'),409
        return jsonify(ok=True,plan=coach.snapshot()['plan'],state=coach.snapshot())
    except ValueError as error:
        return jsonify(error=str(error)),409


@app.get('/profiles')
def profiles():
    rows=owned_profiles(store,g.coach_session['owner'])
    return jsonify(profiles=rows,primary_profile_id=rows[0]['id'] if rows else None,can_create=not bool(rows))


@app.post('/profiles')
def create_profile():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='กรุณาใส่ชื่อผู้เล่น'), 400
    try:
        return jsonify(profile=add_profile(store,g.coach_session['owner'],data.get('name')))
    except ValueError as error:
        return jsonify(error=str(error)), 400


@app.post('/profiles/<int:profile_id>/name')
def change_profile_name(profile_id):
    data=request.get_json(silent=True)
    if not isinstance(data,dict):return jsonify(error='Expected a JSON object'),400
    try:return jsonify(profile=rename_profile(store,g.coach_session['owner'],profile_id,data.get('name')))
    except ValueError as error:return jsonify(error=str(error)),400


@app.post('/health/analyze')
def health_preview():
    try:
        return jsonify(analysis=analyze_health(request.get_json(silent=True)))
    except ValueError as error:
        return jsonify(error=str(error)), 400


@app.route('/profiles/<int:profile_id>/challenges',methods=['GET','POST'])
def profile_challenges(profile_id):
    import challenges
    if request.method=='GET':return jsonify(challenges.overview(store,profile_id))
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict) or data.get('action')!='begin':return jsonify(error='Invalid challenge action'),400
    with sessions.lock:
        if any(item['coach'].state['running'] and (item['coach'].state.get('profile') or {}).get('id')==profile_id for item in sessions.items.values()):
            return jsonify(error='ปิดกล้องก่อนเริ่มชาเลนจ์ / Stop camera before starting a challenge'),409
        return jsonify(challenges.begin(store,profile_id))


@app.route('/profiles/<int:profile_id>/rewards',methods=['GET','POST'])
def profile_rewards(profile_id):
    owner=g.coach_session['owner']
    if request.method=='POST' and not g.account:return jsonify(error='Sign in to exchange / เข้าสู่ระบบเพื่อแลกเหรียญ'),401
    if request.method=='GET':return jsonify(shop.overview(store,owner,profile_id))
    try:return jsonify(shop.act(store,owner,profile_id,request.get_json(silent=True)))
    except PermissionError as error:return jsonify(error=str(error),vip_required=True),403
    except ValueError as error:return jsonify(error=str(error)),400


@app.post('/profiles/<int:profile_id>/orders/<order_id>/cancel')
def cancel_reward(profile_id,order_id):
    # Cancellation remains available after VIP expires; refund belongs to original profile.
    owner=g.coach_session['owner']
    with store.lock,store.connect() as db:
        shop.schema(db)
        row=db.execute('SELECT 1 FROM shop_orders WHERE id=? AND owner=? AND profile_id=?',(order_id,owner,profile_id)).fetchone()
    if not row:return jsonify(error='Order not found'),404
    try:shop.resolve(store,order_id,'cancelled',owner)
    except ValueError as error:return jsonify(error=str(error)),400
    return jsonify(ok=True)


@app.get('/profiles/<int:profile_id>/orders')
def my_reward_orders(profile_id):
    return jsonify(shop.overview(store,g.coach_session['owner'],profile_id))


@app.get('/vip')
def vip_status():
    return jsonify(dict(membership.status(store,g.coach_session['owner']),account_required=not bool(g.account)))


@app.post('/vip/slips')
def vip_slip():
    if not g.account:return jsonify(error='สร้างบัญชีหรือเข้าสู่ระบบก่อนส่งสลิป / Sign in before submitting a receipt'),403
    request.max_content_length=5*1024*1024
    raw=request.stream.read(5*1024*1024+1)
    submit=membership.submit if membership.payment_ready() else membership.submit_manual
    try:return jsonify(submit(store,g.coach_session['owner'],g.account['email'],raw))
    except ValueError as error:return jsonify(error=str(error)),400


@app.get('/vip/slips/<receipt_id>')
def vip_private_slip(receipt_id):
    with store.lock,store.connect() as db:
        membership.schema(db)
        row=db.execute('SELECT image FROM vip_receipts WHERE id=? AND owner=?',(receipt_id,g.coach_session['owner'])).fetchone()
    if not row:return jsonify(error='Receipt not found'),404
    return Response(row['image'],mimetype='image/jpeg',headers={'Cache-Control':'private, no-store'})


@app.get('/profiles/<int:profile_id>/overview')
def profile_overview(profile_id):
    from profile_data import overview
    result=overview(store,profile_id)
    community.profile_roles(store,[result['profile']])
    return jsonify(result)


@app.route('/profiles/<int:profile_id>/avatar',methods=['GET','POST'])
def profile_avatar(profile_id):
    from profile_data import get_avatar,save_avatar
    if request.method=='POST':
        request.max_content_length=3*1024*1024
        if request.content_length and request.content_length>3*1024*1024:
            return jsonify(error='Use an image under 3 MB.'),413
        raw=request.stream.read(3*1024*1024+1)
        try:save_avatar(store,profile_id,raw)
        except ValueError as error:return jsonify(error=str(error)),400
        return jsonify(ok=True)
    raw=get_avatar(store,profile_id)
    if raw is None:return jsonify(error='No avatar'),404
    return Response(raw,mimetype='image/jpeg',headers={'Cache-Control':'private, no-store'})


@app.route('/profiles/<int:profile_id>/character',methods=['GET','POST'])
def profile_character(profile_id):
    try:
        if request.method=='GET':return jsonify(character.overview(store,profile_id,True))
        return jsonify(character.save(store,g.coach_session['owner'],profile_id,request.get_json(silent=True)))
    except PermissionError as error:return jsonify(error=str(error)),403
    except ValueError as error:return jsonify(error=str(error)),400


@app.post('/camera/auto-arm')
def camera_auto_arm():
    data=request.get_json(silent=True)
    if not isinstance(data,dict) or type(data.get('enabled')) is not bool:return jsonify(error='Invalid toggle'),400
    with coach.condition:
        if request.headers.get('X-Set-ID')!=coach.state['set_id']:return jsonify(error='Set changed'),409
        if not coach.state['running'] or coach.state.get('cardio') or coach.state.get('plan') or not training_modes.supports_auto(coach.exercise):return jsonify(error='Use auto arms in a free upper-body workout / ใช้ในเซตช่วงบนแบบอิสระ'),409
        if data['enabled']==(coach.selected_arm=='auto'):return jsonify(ok=True,state=coach.snapshot())
        was_paused=coach.state['paused']
        summary=coach.pause()
        if summary['save_error']:return jsonify(error=summary['save_error']),409
        side=coach.auto_side if coach.selected_arm=='auto' else coach.selected_arm
        if side not in ('left','right'):side='right'
        coach.requested_auto_arm=data['enabled']
        coach.configure(side,coach.user_tolerance,coach.focus,coach.exercise)
        coach.state.update(arm=coach.selected_arm,paused=was_paused,summary=None,set_id=str(uuid.uuid4()))
        coach.last_activity=None;coach.activity_angles={}
        coach.aggregate()
        return jsonify(ok=True,state=coach.snapshot())


@app.get('/profiles/<int:profile_id>/health')
def health_history(profile_id):
    profile = store.profile(profile_id)
    if not profile:
        return jsonify(error='ไม่พบชื่อผู้เล่น'), 404
    return jsonify(profile=profile,records=store.health_history(profile_id))


@app.post('/profiles/<int:profile_id>/health')
def save_health(profile_id):
    try:
        record = store.save_health(profile_id,request.get_json(silent=True))
        character.sync_dimensions(store,profile_id,request.get_json(silent=True))
        return jsonify(record=record)
    except ValueError as error:
        return jsonify(error=str(error)), 400


@app.get('/leaderboard/streaks')
def streak_board():
    return jsonify(rows=community.profile_roles(store,store.streak_standings()),server_today=today_thailand().isoformat())


@app.get('/leaderboard')
def leaderboard():
    exercise, arm = request.args.get('exercise', 'curl'), request.args.get('arm', 'both')
    if exercise not in CATALOG and exercise!='exercise2' or arm not in ('left', 'right', 'both', 'auto'):
        return jsonify(error='ท่าหรือแขนไม่ถูกต้อง'), 400
    return jsonify(exercise=exercise, arm=arm, rows=community.profile_roles(store,store.standings(exercise, arm)), metric='total_saved_reps')


@app.get('/speech/<code>.mp3')
def speech(code):
    if code not in PHRASES:
        return jsonify(error='ไม่มีข้อความเสียงนี้'), 404
    provider = request.args.get('voice','online')
    if provider not in ('online','neural_female','neural_male','openai'):
        return jsonify(error='ตัวเลือกเสียงไม่ถูกต้อง'), 400
    if provider == 'openai' and not voice_cache.configuration()['openai_available']:
        return jsonify(error='เสียง OpenAI ต้องตั้ง OPENAI_API_KEY บนคอมที่รัน Python ก่อน'), 409
    try:
        audio = voice_cache.audio(code) if provider=='online' else voice_cache.audio(code,provider)
        return Response(audio, mimetype='audio/mpeg',
                        headers={'Cache-Control': 'private, max-age=86400'})
    except Exception:
        return jsonify(error='เสียงออนไลน์ไม่พร้อม ตรวจอินเทอร์เน็ต หรือลองเลือกเสียงในอุปกรณ์'), 503


@app.post('/calibrate')
def calibrate():
    coach.recalibrate()
    return jsonify(ok=True)



@app.post('/cardio/start')
def start_cardio():
    data=request.get_json(silent=True)
    if not isinstance(data,dict):return jsonify(error='Invalid game request'),400
    if request.headers.get('X-Set-ID') and request.headers['X-Set-ID']!=coach.state['set_id']:
        return jsonify(error='Cancelled camera operation'),409
    mode=data.get('mode','full');pid=data.get('profile_id')
    if mode not in ('full','upper','pushup') or type(pid) is not int:return jsonify(error='Select a player and mode'),400
    profile=store.profile(pid)
    if not profile:return jsonify(error='Profile not found'),404
    from cardio import options
    try: cardio_options=options(data)
    except ValueError as e:return jsonify(error=str(e)),400
    try:
        if not coach.start('both',0,10,'upper',profile):return jsonify(error='Stop the current session first'),409
        from cardio import JumpingJackRound, PushUpRound
        with coach.condition:
            coach.cardio=(PushUpRound if mode=='pushup' else JumpingJackRound)(store,pid,mode,**cardio_options)
            coach.state['focus']='upper' if mode=='upper' else 'full'
        return jsonify(ok=True,state=coach.snapshot())
    except Exception:
        logging.exception('Cardio start failed')
        return jsonify(error='Cannot start camera; reset and retry'),503

@app.get('/cardio/leaderboard')
def cardio_ranks():
    mode=request.args.get('mode','full')
    if mode not in ('full','upper','pushup'):return jsonify(error='Invalid mode'),400
    from cardio import ranking
    try:tolerance=int(request.args.get('tolerance','10'))
    except ValueError:return jsonify(error='Invalid tolerance'),400
    if not 5<=tolerance<=50:return jsonify(error='Invalid tolerance'),400
    return jsonify(mode=mode,tolerance=tolerance,players=community.profile_roles(store,ranking(store,mode,tolerance)))

@app.post('/frame')
def browser_frame():
    if request.mimetype != 'image/jpeg':
        return jsonify(error='ส่งภาพ JPEG เท่านั้น'),415
    raw=request.get_data()
    if not raw or len(raw)>300000:
        return jsonify(error='ภาพใหญ่เกินไป'),413
    # PIL validates dimensions before OpenCV allocates the decoded frame.
    from PIL import Image
    from io import BytesIO
    try:
        with Image.open(BytesIO(raw)) as probe:
            if probe.format!='JPEG' or not 32<=probe.width<=960 or not 32<=probe.height<=960:
                raise ValueError()
        frame=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError()
    except Exception:
        return jsonify(error='ภาพไม่ถูกต้อง'),400
    try:
        result=coach.accept_frame(frame,request.headers.get('X-Set-ID',''),request.headers.get('X-Frame-Format')=='landmarks')
        with coach.condition:
            if request.headers.get('X-Set-ID')==coach.state['set_id']:coach.frame_failures=0
        return jsonify(result) if isinstance(result,dict) else Response(result,mimetype='image/jpeg')
    except ValueError as error:
        return jsonify(error=str(error)),409
    except Exception:
        logging.exception('Camera frame failed')
        with coach.condition:
            if request.headers.get('X-Set-ID')!=coach.state['set_id']:
                return jsonify(error='Ignored processing error from an older workout'),409
            coach.frame_failures=getattr(coach,'frame_failures',0)+1
            if coach.frame_failures>=3:
                coach.stop()
                coach.release_detector()
        return jsonify(error='ประมวลผลภาพสะดุด กำลังลองใหม่ / Frame interrupted; retrying'),503


@app.get('/video_feed')
def video_feed():
    return jsonify(error='รุ่นนี้ใช้กล้องส่วนตัว กรุณารีเฟรชหน้าเว็บ'),410


import community
community.register(app,lambda:store)
import collaboration_features
collaboration_features.register(app,lambda:store,lambda:sessions,lambda:STABLE_PUBLIC_URL)


@app.get('/profiles/<int:profile_id>/progress')
def profile_progress(profile_id):
    from progress_analysis import report
    return jsonify(report(store,profile_id))

@app.get('/profiles/<int:profile_id>/angles')
def profile_angles(profile_id):
    from angles import history
    return jsonify(history(store,profile_id,request.args.get('day')))


if __name__ == '__main__':
    threading.Thread(target=membership.run_mail_worker,args=(store,),daemon=True).start()
    print('\n45 Fitness Coach\nComputer: http://127.0.0.1:5000/45-fitness-coach', flush=True)
    for link in phone_links():
        print('Phone (same Wi-Fi): ' + link['url'], flush=True)
    print('Camera source: EACH browser. Use HTTPS on phones. Sessions are private.\nCtrl+C stops the server.\n', flush=True)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
