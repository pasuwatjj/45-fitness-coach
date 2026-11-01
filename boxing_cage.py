"""Server-authoritative planar cage movement and timed head-strike resolution."""
import math,uuid,boxing_time
APOTHEM=5.0
SPEED=1.05
RANGE=1.65
MOVE_HOLD=1.0

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
    ps=m['players'];ensure(ps);before=[dict(x=p['x'],z=p['z']) for p in ps]
    for i,p in enumerate(ps):
        dt=max(0,min(now,p.get('control_at',0)+.65)-max(m.get('motion_at',now),m.get('round_start',m.get('start') or now)))
        q=before[1-i] if len(ps)>1 else dict(x=0,z=0);fx,fz=direction(before[i],q)
        side=p.get('side',0) if p.get('side_since') is not None and now-p['side_since']>=MOVE_HOLD else 0
        side_dt=max(0,min(now,p.get('control_at',0)+.65)-max(m.get('motion_at',now),p.get('side_since',now)+MOVE_HOLD)) if side else 0
        # Do not slide the planted support foot during a committed kick.
        kick_start=p.get('kick_at',0);kick_end=p.get('kick_until',0)
        stop=max(0,min(now,p.get('control_at',0)+.65,kick_end)-max(m.get('motion_at',now),m.get('round_start',m.get('start') or now),kick_start))
        side_stop=max(0,min(now,p.get('control_at',0)+.65,kick_end)-max(m.get('motion_at',now),p.get('side_since') or now,kick_start)) if side else 0
        dt=max(0,dt-stop);side_dt=max(0,side_dt-side_stop)
        move=p.get('move',0);scale=max(1,math.hypot(move,side))
        dash_dt=max(0,min(now,p.get('control_at',0)+.65,p.get('dash_until',0))-max(m.get('motion_at',now),p.get('dash_at',0)))
        dash_scale=max(1,math.hypot(p.get('dash_move',0),p.get('dash_side',0)))
        travel=move*max(0,dt-dash_dt)/scale+p.get('dash_move',0)*dash_dt*3.0/dash_scale
        circle=side*max(0,side_dt-dash_dt)/scale+p.get('dash_side',0)*dash_dt*3.0/dash_scale
        pace=p.get('motion_scale',1)
        p['x'],p['z']=clamp(p['x']+(fx*travel+fz*circle)*SPEED*pace,p['z']+(fz*travel-fx*circle)*SPEED*pace)
    if len(ps)==2:
        a,b=ps
        # Sweep relative movement so simultaneous dashes cannot cross through another fighter.
        rx,rz=before[1]['x']-before[0]['x'],before[1]['z']-before[0]['z'];vx,vz=(b['x']-a['x'])-rx,(b['z']-a['z'])-rz
        aa=vx*vx+vz*vz;bb=2*(rx*vx+rz*vz);cc=rx*rx+rz*rz-.8*.8;disc=bb*bb-4*aa*cc
        if aa>1e-10 and bb<0 and cc>=-1e-8 and disc>=0:
            hit=(-bb-math.sqrt(disc))/(2*aa)
            if -1e-8<=hit<1:
                for j,p in enumerate(ps):p['x']=before[j]['x']+(p['x']-before[j]['x'])*max(0,hit);p['z']=before[j]['z']+(p['z']-before[j]['z'])*max(0,hit)
        dx,dz=b['x']-a['x'],b['z']-a['z'];distance=math.hypot(dx,dz)
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
    # Forward/backward move is already gated by the detector's one-second hold.
    if move:ready=True
    if not side and not move:
        p['travel_neutral_at']=neutral if neutral is not None else now
        if not ready:p['side_since']=None
    else:
        p['travel_neutral_at']=None
        if side and (p.get('side_since') is None or (not ready and side!=p.get('side',0))):p['side_since']=now-MOVE_HOLD if ready else now
    p.update(side=side,slip=slip,bend=bend,travel_ready=bool(ready))

def queue(m,p,q,hand,kind,now,token,counter=False):
    ensure(m['players']);fx,fz=direction(p,q)
    m.setdefault('pending_strikes',[]).append(dict(id=uuid.uuid4().hex,attacker=p['uid'],target=q['uid'],hand=hand,punch_type=kind,damage=p.get('kick_damage',1) if kind=='kick' else p['damage'][hand],counter=counter,time=now+(.10 if counter else .28 if kind=='kick' else .18),fx=fx,fz=fz,token=token))

def directional_rules(m):return m.get('rules',0)>=6 and m.get('control_mode')=='computer'

def regenerate(m,now):
    """One armor per five active seconds; zero stays broken until the next round."""
    if not directional_rules(m) or m.get('status')!='active':return
    for p in m['players']:
        anchor=p.get('armor_regen_at',m.get('round_start',m.get('start') or now))
        ticks=max(0,int((now-anchor)//5))
        if ticks:
            if p['armor']>0:p['armor']=min(p.get('max_armor',10),p['armor']+ticks)
            p['armor_regen_at']=anchor+ticks*5

def defend(p,hand,damage,now):
    guarded=p.get('guard_until',0)>now and now-p.get('control_at',0)<.65
    side=p.get('guard_side') or 'both';matched=guarded and side==hand
    armor_loss=0;hp_loss=damage;detail='none'
    if matched and p['armor']>0:hp_loss=0;detail='perfect'
    elif matched:hp_loss=round(damage*.9,2);detail='reduced'
    elif guarded and side=='both':
        armor_loss=min(p['armor'],damage);hp_loss=damage-armor_loss;detail='all' if armor_loss else 'broken'
    elif guarded:detail='wrong'
    p['armor']=max(0,p['armor']-armor_loss);p['hp']=round(max(0,p['hp']-hp_loss),2)
    return dict(result='hit' if hp_loss else 'block',damage=hp_loss if hp_loss else damage,raw_damage=damage,hp_damage=hp_loss,armor_damage=armor_loss,guard_result=detail)

def parry(m,q,strike,now):
    """One opposite-side dash at contact earns one short counter window."""
    at=q.get('dash_at',0)
    return (m.get('rules',0)>=7 and strike['punch_type'] in ('straight','hook')
        and at>0 and at<=strike['time']<=q.get('dash_until',0)+.035
        and now-strike['time']<.65 and q.get('parry_dash_at')!=at
        and q.get('dash_side',0)==(-1 if strike['hand']=='left' else 1))


def resolve(m,now,knockout):
    pending=m.get('pending_strikes',[]);m['pending_strikes']=[]
    for strike in pending:
        if m['status']!='active':break
        if strike['time']>now:m['pending_strikes'].append(strike);continue
        p=next(v for v in m['players'] if v['uid']==strike['attacker']);q=next(v for v in m['players'] if v['uid']==strike['target'])
        dx,dz=q['x']-p['x'],q['z']-p['z'];distance=math.hypot(dx,dz)
        fresh=now-q.get('control_at',0)<.65
        slip=q.get('slip',0) if fresh else 0
        duck=fresh and (now<q.get('dash_until',0) or q.get('bend',0)>.24 or q.get('bend',0)<-.12 or q.get('crouch',0)>.50)
        evade=(strike['hand']=='left' and slip<-.35) or (strike['hand']=='right' and slip>.35)
        defense={};parried=parry(m,q,strike,now)
        if distance>(1.85 if strike['punch_type']=='kick' else RANGE+(.35 if parried else 0)) or (distance>.01 and (dx*strike['fx']+dz*strike['fz'])/distance<.72):result='miss'
        elif parried:
            result='parry';q.update(counter_until=now+.65,parry_dash_at=q['dash_at'])
        elif evade or (duck and strike['punch_type']!='uppercut'):result='dodge'
        elif directional_rules(m):defense=defend(q,strike['hand'],strike['damage'],now);result=defense['result']
        elif q['guard_until']>now and q['armor']>0:q['armor']-=1;result='block'
        else:q['hp']=max(0,q['hp']-strike['damage']);result='hit'
        if m.get('rules',0)>=9 and result in ('dodge','parry') and strike['punch_type']!='kick':
            boxing_time.evade(m,p,q);q['counter_until']=now+.65
            defense.update(slow_target=p['uid'],slow_until=p['evade_slow_until'])
        if result=='hit' and m.get('rules',0)>=7:
            fx,fz=direction(p,q);push=.18 if strike['punch_type']=='uppercut' else .14
            old_x,old_z=q['x'],q['z'];q['x'],q['z']=clamp(q['x']+fx*push,q['z']+fz*push)
            defense['knockback']=dict(x=q['x']-old_x,z=q['z']-old_z);q['hit_at']=now
        event={k:v for k,v in strike.items() if k not in ['fx','fz','token']};event.update(defense);event.update(result=result,time=now,x=q['x'],z=q['z'])
        m['event']=event;m['events']=(m.get('events',[])+[event])[-12:]
        if q['hp']==0:knockout(m,p,now);m['pending_strikes']=[];break
