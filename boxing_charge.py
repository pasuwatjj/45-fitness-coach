"""Charge time is measured by the server's combat clock, never client damage."""
FULL = 1.5
GRACE = .7


def reset(player):
    player.pop('charge_hand', None)
    player.pop('charge_at', None)


def update(player, hand, now, allowed):
    previous = player.get('charge_hand')
    fresh = now - player.get('control_at', 0) <= GRACE
    age = max(0, now - player.get('charge_at', now)) if fresh and previous else 0
    if not allowed or not hand:
        reset(player)
    elif hand != previous or not fresh:
        player.update(charge_hand=hand, charge_at=now)
    return previous if fresh and allowed else None, min(FULL, age)


def multiplier(seconds):
    return 1 + max(0, min(1, (seconds - .2) / (FULL - .2)))
