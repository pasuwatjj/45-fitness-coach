"""Server-owned combat clock. Skill duration/cooldown use real time, combat uses game time."""
SLOW_RATE=.4
DURATION=60
COOLDOWN=180

def sync(m,wall):
    previous=m.get('clock_wall',wall);wall=max(wall,previous);game=m.get('combat_now',previous)
    end=m.get('slow_until',0)
    slow=max(0,min(wall,end)-previous) if m.get('status')=='active' else 0
    m['combat_now']=game+max(0,wall-previous)-slow*(1-SLOW_RATE)
    m['clock_wall']=wall
    m['time_scale']=SLOW_RATE if m.get('status')=='active' and wall<end else 1
    return m['combat_now']

def activate(m,p,wall):
    if m['status']!='active':raise ValueError('Skill is available during a round')
    if wall<m.get('slow_until',0):raise ValueError('Slow motion is already active')
    if wall<p.get('skill_ready_at',0):raise ValueError('Skill is cooling down')
    p['skill_ready_at']=wall+COOLDOWN
    m.update(slow_until=wall+DURATION,slow_by=p['uid'],time_scale=SLOW_RATE)


def evade_sync(m,wall,previous_wall,previous_game):
    """Pause only the dodged attacker's combat timers, preserving remaining recovery."""
    total=max(0,m['combat_now']-previous_game)
    for p in m['players']:
        end=min(wall,p.get('evade_slow_until',0));duration=max(0,end-previous_wall)
        if m.get('status')!='active':duration=0
        shared=max(0,min(end,m.get('slow_until',0))-previous_wall) if duration else 0
        loss=(duration-shared*(1-SLOW_RATE))*(1-SLOW_RATE)
        p['motion_scale']=max(SLOW_RATE,1-loss/total) if total else 1
        if not loss:continue
        starts={'last_punch':.76 if p.get('punch_type')=='kick' else .4,'last_dash':.65,'hit_at':.32}
        for key,length in starts.items():
            if p.get(key,0)>0 and previous_game-p[key]<length:p[key]+=loss
        for start,end_key in [('dash_at','dash_until'),('kick_at','kick_until')]:
            if p.get(end_key,0)>previous_game:
                p[start]=p.get(start,previous_game)+loss;p[end_key]+=loss
        for key in ['guard_until','counter_until','dodge_until']:
            if p.get(key,0)>previous_game:p[key]+=loss
        if p.get('armor_regen_at') is not None:p['armor_regen_at']+=loss
        for strike in m.get('pending_strikes',[]):
            if strike['attacker']==p['uid']:strike['time']+=loss
        if p.get('bot'):
            for key in ['next_tick','next_attack','next_choice']:
                if m.get('brain',{}).get(key,0)>previous_game:m['brain'][key]+=loss


def evade(m,attacker,defender):
    attacker.update(evade_slow_until=m['clock_wall']+5,evade_slow_by=defender['uid'])
