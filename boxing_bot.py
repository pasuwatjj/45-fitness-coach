"""Bounded, server-owned sparring decisions. Only delayed, visible poses are observed."""
from copy import deepcopy
import math
import boxing_cage as cage


def create(player, difficulty, now):
    bot = deepcopy(player)
    bot.update(uid=-1, profile_id=None, name='NOVA · '+difficulty.upper(), bot=True, ready=True, seen=now)
    # Appearance changes only. Growth, body dimensions and damage stay identical.
    bot['model'].setdefault('appearance', {}).update(hair='short', hair_color='#dce5ec',
        top_color='#258eaa' if difficulty=='easy' else '#b13a55', shorts_color='#182635')
    return bot


def roll(brain):
    brain['seed']=(1664525*brain['seed']+1013904223) % 2**32
    return brain['seed']/2**32


def policy(difficulty, round_number, learned):
    hard=difficulty=='hard'
    # Easy round one never adapts; later rounds remain deliberately forgiving.
    strength=1 if hard else min(.42,.18+.10*(round_number-1))
    total=learned.get('left',0)+learned.get('right',0)
    favorite=('left' if learned.get('left',0)>=learned.get('right',0) else 'right') if total>=3 else None
    return dict(reaction=.14 if hard else .42, aggression=.58 if hard else 1.65-.12*min(2,round_number-1),
                defense=strength, favorite=favorite if hard or round_number>1 else None,
                duck=learned.get('duck',0)>learned.get('samples',0)*.3 if learned.get('samples') else False)


def tick(m, now, act):
    bot=next(p for p in m['players'] if p.get('bot'));human=next(p for p in m['players'] if not p.get('bot'))
    bot['seen']=now
    if m['status']!='active':return
    brain=m['brain'];cage.ensure(m['players'])
    if now<brain.get('next_tick',0):return
    brain['next_tick']=now+.10
    if brain.get('round')!=m['round']:
        brain['round']=m['round'];brain['learned']=deepcopy(brain.get('observed',{}))
        brain['plan']=policy(m['difficulty'],m['round'],brain['learned'])
        brain['observed']={};brain['history']=[];brain['next_attack']=now+(1.2 if m['difficulty']=='easy' else .5)
        brain['next_choice']=0;brain['last_seen_strike']=None
    plan=brain['plan'];observed=brain['observed']
    fresh=now-human.get('control_at',0)<.65
    sample=dict(at=now,hand=human.get('last_hand'),punch_at=human.get('last_punch',0),
        kind=human.get('punch_type','straight'),guard=human.get('guard_until',0)>now,
        guard_side=human.get('guard_side'),duck=fresh and (human.get('crouch',0)>.5 or abs(human.get('bend',0))>.24))
    history=brain['history'];history.append(sample);brain['history']=history[-18:]
    visible=next((s for s in reversed(history) if s['at']<=now-plan['reaction']),None)
    if not visible:return
    if visible['punch_at'] and visible['punch_at']!=brain.get('last_seen_strike'):
        brain['last_seen_strike']=visible['punch_at'];hand=visible['hand']
        observed[hand]=observed.get(hand,0)+1
    observed['samples']=observed.get('samples',0)+1;observed['duck']=observed.get('duck',0)+int(visible['duck'])
    hard=m['difficulty']=='hard';computer=m.get('control_mode')=='computer'
    if hard:plan=policy('hard',m['round'],observed) # Adapt continuously, with delayed reactions below.
    if now>=brain.get('next_choice',0):
        brain['next_choice']=now+(.38 if hard else .8)
        brain['evasive']=hard and roll(brain)<.28
        brain['defending']=roll(brain)<plan['defense'];brain['circle']=(-1 if roll(brain)<.5 else 1) if hard or roll(brain)<.25 else 0
    distance=math.hypot(bot['x']-human['x'],bot['z']-human['z'])
    data=dict(action='control',seq=bot['seq']+1,input_source='keyboard' if computer else 'camera',
              move=1 if distance>1.35 else -1 if distance<.95 else 0,strafe=brain['circle'] if computer else 0,
              slip=0,bend=0,crouch=0,guard=False,guard_side=None)
    incoming=visible['hand'] if 0<=now-visible['punch_at']<.52 else None
    favorite=plan['favorite']
    if brain['defending'] and distance<1.85:
        data.update(guard=True,guard_side=(incoming or favorite or 'both') if computer else 'both')
        # Committed reaction to a visible attack, never to a queued future input.
        if hard and ((incoming and now-visible['punch_at']<.32 and visible['kind']!='uppercut') or brain['evasive']):
            predicted=incoming or favorite or ('left' if brain['circle']<0 else 'right')
            side=-1 if predicted=='left' else 1
            data.update(guard=False,guard_side=None,slip=side*.75)
            if computer:data.update(dash=True,strafe=side,move=0)
    counter=bot.get('counter_until',0)>now
    opening=hard and incoming and .22<now-visible['punch_at']<.5 and not visible['guard'] and now-bot['last_punch']>.5
    if distance<=1.6 and (now>=brain['next_attack'] or counter or opening):
        hand='left' if roll(brain)<.5 else 'right'
        if hard and visible['guard'] and visible['guard_side'] in ('left','right'):hand='right' if visible['guard_side']=='left' else 'left'
        kind='uppercut' if (hard and visible['duck']) or (m['round']>1 and plan['duck'] and roll(brain)<.5) else 'hook' if roll(brain)<.35 else 'straight'
        data.update(action=hand,punch_type=kind,strike_id='bot:'+str(bot['seq']+1),guard=False,guard_side=None,slip=0,dash=False)
        brain['next_attack']=now+plan['aggression']+roll(brain)*(.3 if hard else .7)
    act(m,bot['uid'],data,now,internal_bot=True)
