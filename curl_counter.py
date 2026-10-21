"""Geometry and rep counter. Thresholds are prototype settings, not clinical rules."""
import math


def elbow_angle(a, b, c):
    u = tuple(x - y for x, y in zip(a, b))
    v = tuple(x - y for x, y in zip(c, b))
    length = math.hypot(*u) * math.hypot(*v)
    if length < 1e-6:
        return None
    cosine = sum(x*y for x, y in zip(u, v)) / length
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


class CurlCounter:
    def __init__(self):
        self.reps = 0
        self.reset_phase()

    def reset_phase(self):
        self.phase = 'waiting'
        self.pending = None
        self.pending_since = 0
        self.raised_at = 0
        self.minimum = 180
        self.maximum = 0
        self.last_angle = None

    def reset(self):
        self.reps = 0
        self.reset_phase()

    def update(self, angle, now_ms, down=150, up=60, minimum_excursion=0):
        if self.phase != 'waiting':
            self.minimum = min(self.minimum, angle)
            self.maximum = max(self.maximum, angle)
        target = 'down' if angle >= down else 'up' if angle <= up else None
        if target != self.pending:
            self.pending, self.pending_since = target, now_ms
        previous_angle=self.last_angle
        self.last_angle=angle
        # A moving arm can cross the endpoint briefly without holding still.
        # Require an observed intermediate angle and a wide excursion, not a
        # mandatory dwell at the endpoint. Sustained endpoints remain supported.
        crossing=(previous_angle is not None and up < previous_angle < down
                  and self.maximum-self.minimum >= minimum_excursion)
        if target is None or (now_ms-self.pending_since < 120 and not crossing):
            return False
        if self.phase == 'waiting' and target == 'down':
            self.phase = 'ready'
            self.minimum = self.maximum = angle
        elif self.phase == 'ready' and target == 'up':
            self.phase, self.raised_at = 'raised', now_ms
        elif self.phase == 'raised' and target == 'down':
            counted = self.maximum - self.minimum >= minimum_excursion
            self.reps += int(counted)
            self.phase = 'ready'
            self.minimum = self.maximum = angle
            return counted
        return False
