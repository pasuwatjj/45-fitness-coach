# Upper-body controlled 3D cage

The boxing room now uses a single Three.js scene for both existing profile avatars, the cage, lighting, shadows and the practice bag. The visual direction follows the user's Ultimate MMA / Muay Thai Fighting Origins references: a raised fighting arena, close ringside view, opponent-facing movement and visible contact feedback. The cage, audience, signs, floor art and bag are original procedural geometry/textures. Saved Quaternius characters, appearance and growth remain unchanged; cage-only pelvis, lumbar, chest and neck joints distribute bends and lateral slips along the torso.

## Playing

- Frame your head, shoulders, elbows and hands, then stand upright for calibration. No knee, ankle or foot landmarks are needed. Hips, when visible, improve the torso estimate; head/shoulder depth and image-space displacement provide the cropped-view fallback.
- A short lean is a dodge without translation. Hold a gentle forward/back lean for two continuous seconds to approach/retreat; the same hold applies laterally. Detection begins around 10° forward or 6° backward relative to calibration, with a 3° neutral dead zone. Bend or lower the upper body to duck; deeper bows suppress forward travel. Feet animate in the game.
- Slip left/right immediately. Against an opponent's left punch, slip right; against their right, slip left. Hold the same lean continuously for two seconds to circle in that direction. After the first two-second hold, direction can change immediately, including switching between forward/back and lateral movement. Crossing neutral for less than 250 ms keeps this unlocked; neutral stops movement immediately and rearms after 250 ms. Lost/stale tracking also rearms. The server verifies the lateral hold and retains the unlocked state across direction changes.
- Straight punches, hooks, uppercuts and short forearm jabs are recognized. The horizontal shoulder frame converts camera coordinates into body-relative directions, including side-on punches. Full normalized shoulder–elbow and elbow–wrist directions drive the arms continuously, without compressing lateral reach, stretching bone lengths, or forcing each scoring event into a preset arm animation. Retract to a neutral position and settle for 180 ms before another strike. Retraction itself is never classified as a strike; held extensions and jitter do not repeat. Temporary tracking loss requires neutral recovery/calibration. A separate camera-session strike counter survives detector recalibration.
- Hold both elbows near shoulder height for three seconds to guard. Armor is consumed only by a blocked impact. Slips/ducks and movement cost no armor. Uppercuts can counter a deep duck.
- The bag is at the arena center in Training. Friend mode waits in the invitation lobby and loads a two-fighter arena after both cameras are ready. Hits show projected damage numbers and bag motion. Both players see HP/armor and match damage feedback.
- Drag to orbit, scroll/pinch to zoom, or select Ringside, Boxing camera, Overhead and Full screen. The default Boxing camera is a close, low over-shoulder view of the current player, with adaptive distance and smoothed yaw. Ringside tracks the line between the fighters. A higher view shows the fallen fighter during the count.
- Matches remain best of three (first to two knockouts), with a ten-second knockdown count, fresh HP/armor each round and one 45 championship belt recorded on the winner's profile. The clock counts active round time. Instructions are also available in Thai/English under the arena.

## Mechanics and compatibility

New rooms use rules version 5. Server-owned planar coordinates constrain movement to the octagon, normalize diagonal speed and separate overlapping fighters. Opponent-facing movement combines radial approach/retreat with tangential circling. Stale controls expire after 650 ms. Strikes have a 180 ms windup and then resolve range, captured aim direction, fresh directional slip/duck, guard and HP in that order. Recent strike IDs and event sequence numbers prevent repeat damage. Finishing a match clears pending impacts. Existing version 2/3/4 rooms retain their original server rules; no account/profile migration is needed.

The browser interpolates snapshots and animates the approved skeleton in the shared renderer. Only normalized arm vectors and control values are sent; camera frames remain local. This is a casual HTTP-synchronized game with explicit evasion rules, not a full rigid-body martial arts simulation. Device tracking quality and connection latency still affect responsiveness.

## Contact and pose constraints

Swept glove tests against moving capsules on the opponent's arms, torso and head, plus the practice bag, cage and canvas constrain the visual arm pose. Fixed-length two-bone IK keeps the glove outside contact; elbow swivel and chain retraction clear obstructed upper arms/forearms. Retraction releases contact. Fast extensions are swept rather than checking only the final wrist position. Both fighters use the same pre-constraint pose snapshot. This approximates body surfaces; it is not mesh-level rigid-body physics or a new authoritative damage model. Damage still follows server range, timed strike, evasion and guard rules, so visual contact is not used as a trusted client damage claim.

Shoulder-width changes no longer cause false backward travel when turning. Back extension is capped, waist/head pitch uses the body frame, and visible torso compression assists bowing. An idle thoracic curve and chin tuck carry into punches. Short occlusion holds the last arm pose, then returns to guard; invalid/degenerate limb segments cannot trigger a strike. Calibration should face the camera; severely occluded landmarks remain a tracking limitation.

`tests/qa_boxing_contacts.py` exercises bag and guard contact, fast sweeps, both arm links, release, preserved lengths and actual default camera framing at desktop/phone sizes.

## Reference study

- User-supplied Ultimate MMA and Hajime no Ippo screenshots: close over-shoulder framing, curved boxing posture and a canvas knockdown/count. No game assets were copied.
- [MediaPipe Pose documentation](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/pose.md): landmark visibility, normalized/world coordinate conventions and smoothing.
- [Three.js r160 skinned animation example](https://github.com/mrdoob/three.js/blob/r160/examples/webgl_animation_skinning_blending.html): shared animated scene, frame delta and lighting/shadows.
- [Three.js r160 OrbitControls](https://github.com/mrdoob/three.js/blob/r160/examples/jsm/controls/OrbitControls.js): orbit target, angle limits, zoom and touch interaction. This project's small camera controller is implemented locally.
- [BoxingVR overview](https://github.com/josericardopenase/BoxingVR): practice-bag impact feedback and damped movement reference. No source or assets were copied from that project.

## Verification

Use disposable local data and the existing `.venv`; never run account-creating QA against production.

```sh
FITNESS_DATA_PATH="$PWD/work/cage-test.db" MPLCONFIGDIR="$PWD/work/mpl" .venv/bin/flask --app app run --port 5055
node tests/test_boxing_pose.cjs
.venv/bin/python -m unittest test_boxing test_boxing_cage
.venv/bin/python tests/qa_boxing_championship.py
.venv/bin/python tests/qa_boxing_menu.py
.venv/bin/python tests/qa_boxing_natural.py
.venv/bin/python tests/qa_boxing_natural_controls.py
node tests/test_avatar_browser.cjs
```

The championship browser test runs two accounts at 1280 px and 390 px with real browser fake-camera streams and synthetic upper-body landmarks. It covers forward/back movement, crouch/stand, torso bend, two-second circling without hips/legs, camera views/orbit/zoom, fullscreen and fallback, reduced motion, English/Thai, center bag damage, directional evasion, recoil suppression, a complete 2–1 match, per-round reset and one final belt. Dedicated route/geometry cases cover timing, stale signals, boundaries/collision, guard, duck/uppercut, range, invalid controls and strike-ID replay. The avatar regression covers customization, save/reload and rotation.

Physical webcam accuracy has not been measured on the user's camera. The read-only deployment verifier checks the exact release revision/assets and exercises a shared scene with the public avatar assets without creating live accounts.

The current change is checked with root Python and installer/source tests, detector fixtures, the championship flow, and the natural-rig/control regressions above. The rig check measures full arm-chain reach, preserves short-jab extension during the impact envelope, verifies finite normalized skin weights, and exercises both saved avatar genders. Browser animation assertions wait for rendered state rather than assuming that a software renderer completes an animation on a fixed wall-clock frame.

Review images: [ringside](ringside.png), [solo practice](practice.png), [overhead](overhead.png), [mobile](mobile.png).

## Knockdown and championship belt

A non-final knockout starts a ten-second server-timed recovery: the loser falls onto their back, begins rising at 8.2 seconds, and is back in guard before the next round. Both clients use the same knockout timestamp. Tracking cannot override the recovery pose, and attacks are rejected during the break. On the deciding knockout (a 2–0 or 2–1 result), the loser remains lying through the full ten-second count before the result is awarded; the winner then raises both arms with the original black-and-gold 45 belt, framed by a victory camera and localized result panel. Reduced-motion settings retain the readable result without decorative flashes.

The profile now shows a belt collection. The existing unique-per-match reward ledger is retained so previous victories are preserved; `/social/boxing/belts/<profile>` is the new authenticated endpoint and the old trophy route remains compatible. The reward still belongs to the winning profile and is not duplicated by polling, reopening a match or refreshing the profile. Existing disconnect/forfeit reward rules are unchanged; leaving before a fight starts does not earn a belt.

`tests/qa_boxing_belts.py` checks lying foot clearance, timed recovery, final KO persistence, both avatar genders, visible belt and cleanup. The championship browser test checks both clients through a 2–1 match and the winner's profile; route tests cover 2–0, historical reward preservation and ownership. `tests/verify_live_boxing.py` checks exact deployed assets and read-only knockdown/belt rendering.
