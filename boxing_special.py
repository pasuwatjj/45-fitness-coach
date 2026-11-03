"""Server-owned Ruesi Bod Ya cinematic. Rule 11 adds defensive aim and half-max-HP damage."""
import math,uuid,boxing_aim
DURATION=6.2
IMPACT=4.1
COOLDOWN=180
RANGE=4.0

def active(m,wall):
    s=m.get('special')
    return bool(s and m.get('status')=='active' and wall<s['started_at']+s['duration'])

def activate(m,p,wall):
    if m['status']!='active':raise ValueError('Skill is available during a round')
    if active(m,wall):raise ValueError('A cinematic skill is already active')
    if wall<p.get('special_ready_at',0):raise ValueError('Skill is cooling down')
    q=next(v for v in m['players'] if v['uid']!=p['uid'])
    if math.hypot(q['x']-p['x'],q['z']-p['z'])>RANGE:raise ValueError('Move within 4 metres to use Ruesi Bod Ya')
    p['special_ready_at']=wall+COOLDOWN
    m['special']=dict(id=uuid.uuid4().hex,attacker=p['uid'],target=q['uid'],started_at=wall,duration=DURATION,impact=IMPACT,damage=p['damage']['right'],players=[dict(uid=v['uid'],x=v['x'],z=v['z']) for v in m['players']])
    if m.get('rules',0)>=11:
        challenge=boxing_aim.create(q,wall)
        lead=boxing_aim.DURATION+boxing_aim.GRACE
        m['special'].update(challenge=challenge,phase='aim',cinematic_at=wall+lead,duration=lead+DURATION,impact=lead+IMPACT,damage=round(q['max_hp']*.5,2))
    m['pending_strikes']=[]
    for v in m['players']:
        v.update(charge_hand=None,charge_at=0,move=0,side=0,side_since=None,crouch=0,slip=0,bend=0,arms=None,posture=None,lowerBody=None,guard_until=0,counter_until=0,evade_slow_until=0,dash_until=0,kick_until=0,last_punch=0,last_hand=None)

def advance(m,wall,knockout):
    s=m.get('special')
    if not s or s.get('complete') or m['status']!='active':return
    age=wall-s['started_at'];p=next(v for v in m['players'] if v['uid']==s['attacker']);q=next(v for v in m['players'] if v['uid']==s['target'])
    if age>=s['impact'] and not s.get('applied'):
        s['applied']=True;damage=min(q['hp'],s['damage']);q['hp']=round(max(0,q['hp']-damage),2)
        event=dict(id=s['id'],attacker=p['uid'],target=q['uid'],hand='right',punch_type='elbow',special=True,result='hit',damage=damage,hp_damage=damage,armor_damage=0,time=m['combat_now'],x=q['x'],z=q['z'])
        m['event']=event;m['events']=(m.get('events',[])+[event])[-12:]
    if age>=s['duration']:
        s['complete']=True
        for v in m['players']:v.update(control_at=0,move=0,side=0,guard_until=0)
        if q['hp']==0:knockout(m,p,m['combat_now'])
