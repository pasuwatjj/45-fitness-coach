# Boxing movement, reach and practice

The solo arena now has a reusable punching bag. Camera-driven forward/backward movement works before pairing, including while an invitation is pending. Practice counts landed punches and damage locally; it never awards trophies or consumes HP/armor. The bag disappears when the friend joins.

Body control no longer requires both wrists to remain visible. Missing hands disable their punches/guard while head/shoulder tracking can still move the fighter. Torso tilt uses a calibrated 18-degree start and 9-degree neutral stop with smoothing; an upper-body crop can use head-to-shoulder depth. Losing the head/shoulders resets movement and calibration. Front/back remains relative to the fighter's fixed facing direction.

Punches now have a deliberate extension/return animation, reaching 10% farther visually at full extension. Authoritative match hit distance increases from .39 to .44 arena widths. Damage remains the saved arm level. Both clients display hit damage, armor loss or a miss above the target. A bounded recent-event list avoids dropping simultaneous punches between polls; event IDs prevent repeated popups.

## Validation

- 325 root tests and 25 tests under `tests/` pass, including range, movement/stop without armor loss and recent events.
- `node tests/test_boxing_pose.cjs`: depth punches, retraction, guard hold, gentle tilt in both directions, cropped hips, missing wrists and confidence reset.
- `tests/qa_boxing_practice.py`: Chromium at 1280 and 390 px with fake local camera streams and synthetic landmarks exercises the real camera loop, bag hit/miss, extension/retraction, solo and two-player movement, neutral stop, HP/armor popups and event deduplication.
- Existing `tests/qa_boxing.py`: friendship/inbox invitation, readiness/countdown, camera privacy, arm sync, guard, disconnect and trophy persistence pass.
- Browser accounts use disposable local databases. These tests do not replace testing with the user's physical camera and lighting.

[Desktop](1280-practice.png) · [Mobile](390-practice.png). Screenshots freeze the real punch animation briefly for review; no avatar or damage elements are fabricated.
