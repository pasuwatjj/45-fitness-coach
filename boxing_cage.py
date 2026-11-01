"""Server-authoritative planar cage movement and timed head-strike resolution."""
import math,uuid
APOTHEM=5.0
SPEED=1.05
RANGE=1.65
MOVE_HOLD=2.0

def clamp(x,z):
    for _ in range(2):
        for i in range(8):
            nx,nz=math.cos(i*math.pi/4),math.sin(i*math.pi/4)
            excess=x*nx+z*nz-APOTHEM
            if excess>0:x-=nx*excess;z-=nz*excess
    return x,z

def ensure(players):
    for i,p in enumerate(players):
        if 'x' not in p:p.update(x=-.7 if i==0 else .7,z=0)

def direction(p,q):
    dx,dz=q['x']-p['x'],q['z']-p['z'];length=math.hypot(dx,dz)
    return (dx/length,dz/length) if length>.001 else (1,0)

def motion(m,now):
    ps=m['players'];ensure(ps)
    for i,p in enumerate(ps):
        dt=max(0,min(now,p.get('control_at',0)+.65)-max(m.get('motion_at',now),m.get('round_start',m.get('start') or now)))
        q=ps[1-i] if len(ps)>1 else dict(x=0,z=0);fx,fz=direction(p,q)
        side=p.get('side',0) if p.get('side_since') is not None and now-p['side_since']>=MOVE_HOLD else 0
        side_dt=max(0,min(now,p.get('control_at',0)+.65)-max(m.get('motion_at',now),p.get('side_since',now)+MOVE_HOLD)) if side else 0
        move=p.get('move',0);scale=max(1,math.hypot(move,side))
        p['x'],p['z']=clamp(p['x']+(fx*move*dt+fz*side*side_dt)*SPEED/scale,p['z']+(fz*move*dt-fx*side*side_dt)*SPEED/scale)
    if len(ps)==2:
        a,b=ps;dx,dz=b['x']-a['x'],b['z']-a['z'];distance=math.hypot(dx,dz)
        if distance<.8:
            nx,nz=(dx/distance,dz/distance) if distance>.001 else (1,0);amount=(.8-distance)/2
            a['x'],a['z']=clamp(a['x']-nx*amount,a['z']-nz*amount);b['x'],b['z']=clamp(b['x']+nx*amount,b['z']+nz*amount)
    m['motion_at']=now

def control(p,slip,bend,now,move=0):
    side=1 if slip>.35 else -1 if slip<-.35 else 0
    fresh=now-p.get('control_at',0)<=.7
    neutral=p.get('travel_neutral_at')
    ready=fresh and (p.get('travel_ready',False) or (p.get('side_since') is not None and p.get('side',0) and now-p['side_since']>=MOVE_HOLD))
    if not fresh or (neutral is not None and now-neutral>=.25):ready=False;p['side_since']=None
    # Forward/backward move is already gated by the detector's two-second hold.
    if move:ready=True
    if not side and not move:
        p['travel_neutral_at']=neutral if neutral is not None else now
        if not ready:p['side_since']=None
    else:
        p['travel_neutral_at']=None
        if side and (p.get('side_since') is None or (not ready and side!=p.get('side',0))):p['side_since']=now-MOVE_HOLD if ready else now
    p.update(side=side,slip=slip,bend=bend,travel_ready=bool(ready))

def queue(m,p,q,hand,kind,now,token):
    ensure(m['players']);fx,fz=direction(p,q)
    m.setdefault('pending_strikes',[]).append(dict(id=uuid.uuid4().hex,attacker=p['uid'],target=q['uid'],hand=hand,punch_type=kind,damage=p['damage'][hand],time=now+.18,fx=fx,fz=fz,token=token))

def resolve(m,now,knockout):
    pending=m.get('pending_strikes',[]);m['pending_strikes']=[]
    for strike in pending:
        if m['status']!='active':break
        if strike['time']>now:m['pending_strikes'].append(strike);continue
        p=next(v for v in m['players'] if v['uid']==strike['attacker']);q=next(v for v in m['players'] if v['uid']==strike['target'])
        dx,dz=q['x']-p['x'],q['z']-p['z'];distance=math.hypot(dx,dz)
        fresh=now-q.get('control_at',0)<.65
        slip=q.get('slip',0) if fresh else 0
        duck=fresh and (q.get('bend',0)>.24 or q.get('bend',0)<-.12 or q.get('crouch',0)>.50)
        evade=(strike['hand']=='left' and slip<-.35) or (strike['hand']=='right' and slip>.35)
        if distance>RANGE or (distance>.01 and (dx*strike['fx']+dz*strike['fz'])/distance<.72):result='miss'
        elif evade or (duck and strike['punch_type']!='uppercut'):result='dodge'
        elif q['guard_until']>now and q['armor']>0:q['armor']-=1;result='block'
        else:q['hp']=max(0,q['hp']-strike['damage']);result='hit'
        event={k:v for k,v in strike.items() if k not in ['fx','fz','token']};event.update(result=result,time=now,x=q['x'],z=q['z'])
        m['event']=event;m['events']=(m.get('events',[])+[event])[-12:]
        if q['hp']==0:knockout(m,p,now);m['pending_strikes']=[];break
