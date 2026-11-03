"""Authoritative, wall-clock defensive challenge for rule 11 X attacks."""
import random
import uuid

DURATION = 10
GRACE = .18


def create(target, wall):
    urgent = target['hp'] < target['max_hp'] * .5
    windows = [1.55 - i * 1.1 / 9 for i in range(10)] if urgent else [1.25] * 8
    slots = [(x, y) for y in (.22, .5, .78) for x in (.18, .5, .82)]
    targets = []
    start = wall
    previous = None
    for duration in windows:
        position = random.choice([p for p in slots if p != previous])
        targets.append(dict(id=uuid.uuid4().hex, x=position[0], y=position[1],
                            opens_at=start, closes_at=start + duration, hit=False))
        start += duration
        previous = position
    return dict(started_at=wall, ends_at=wall+DURATION, resolve_at=wall+DURATION+GRACE,
                urgent=urgent, targets=targets, stray_misses=0, status='active')


def click(match, player, data, wall):
    special = match.get('special') or {}
    challenge = special.get('challenge')
    if not challenge or match['status'] != 'active':
        return
    if player['uid'] != special['target']:
        raise ValueError('Only the defender can play the aim challenge')
    if data.get('special_id') != special['id'] or challenge['status'] != 'active':
        return
    target_id = data.get('target_id')
    if target_id is None:
        if challenge['started_at'] <= wall < challenge['ends_at']:
            challenge['stray_misses'] += 1
        return
    target = next((t for t in challenge['targets'] if t['id'] == target_id), None)
    if target and not target['hit'] and target['opens_at'] <= wall <= target['closes_at'] + GRACE:
        target['hit'] = True


def prepare(match, wall):
    """Resolve before syncing combat time so an evade ends the pause precisely."""
    special = match.get('special') or {}
    challenge = special.get('challenge')
    if not challenge or challenge['status'] != 'active' or match['status'] != 'active':
        return
    defender = next(p for p in match['players'] if p['uid'] == special['target'])
    if defender.get('bot'):
        # Server-owned reaction times; fast closing windows can beat the bot.
        reaction = .48 if match.get('difficulty') == 'hard' else .9
        for target in challenge['targets']:
            if target['opens_at'] + reaction <= min(wall, target['closes_at']):
                target['hit'] = True
    if wall < challenge['resolve_at']:
        return
    escaped = not challenge['stray_misses'] and all(t['hit'] for t in challenge['targets'])
    challenge['status'] = 'evaded' if escaped else 'failed'
    special['phase'] = 'evaded' if escaped else 'cinematic'
    if escaped:
        special.update(complete=True, duration=DURATION+GRACE)
        event = dict(id=special['id'], attacker=special['attacker'], target=special['target'],
                     special=True, result='special_evade', damage=0, hp_damage=0,
                     time=match.get('combat_now', wall))
        match['event'] = event
        match['events'] = (match.get('events', []) + [event])[-12:]
