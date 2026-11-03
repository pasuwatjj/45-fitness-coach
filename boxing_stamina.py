"""Rule 10 stamina: 20 capacity, 2 per punch, 5 per real second at rest/guard."""
MAXIMUM = 20
COST = 2
RATE = 5
REST_DELAY = .65


def advance(match, wall, game):
    if match.get('rules', 0) < 10:
        return
    for player in match['players']:
        player.setdefault('stamina', MAXIMUM)
        previous = player.get('stamina_at', wall)
        if match['status'] == 'active' and not (match.get('special') and not match['special'].get('complete')):
            guarding = player.get('guard_until', 0) > game
            start = previous if guarding else max(previous, player.get('stamina_spent_at', wall - REST_DELAY) + REST_DELAY)
            special = match.get('special') or {}
            if special.get('complete') and 'started_at' in special:
                start = max(start, special['started_at'] + special['duration'])
            player['stamina'] = round(min(MAXIMUM, player['stamina'] + max(0, wall - start) * RATE), 4)
        player['stamina_at'] = wall


def spend(match, player, kind):
    if match.get('rules', 0) < 10 or kind == 'kick':
        return True
    value = player.get('stamina', MAXIMUM)
    if value < COST:
        return False
    player['stamina'] = round(value - COST, 4)
    player['stamina_spent_at'] = match.get('clock_wall', match.get('combat_now', 0))
    return True
