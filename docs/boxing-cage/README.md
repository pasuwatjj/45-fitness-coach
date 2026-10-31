# Upper-body controlled 3D cage

The boxing room now uses a single Three.js scene for both existing profile avatars, the cage, lighting, shadows and the practice bag. The visual direction follows the user's Ultimate MMA / Muay Thai Fighting Origins references: a raised fighting arena, close ringside view, opponent-facing movement and visible contact feedback. The cage, audience, signs, floor art and bag are original procedural geometry/textures. Saved Quaternius characters, appearance and growth remain unchanged; cage-only pelvis, lumbar, chest and neck joints distribute bends and lateral slips along the torso.

## Playing

- Frame your head, shoulders, elbows and hands, then stand upright for calibration. No knee, ankle or foot landmarks are needed. Hips, when visible, improve the torso estimate; head/shoulder depth and image-space displacement provide the cropped-view fallback.
- A short lean is a dodge without translation. Hold a gentle forward/back lean for two continuous seconds to approach/retreat; the same hold applies laterally. Detection begins around 10° forward or 6° backward relative to calibration, with a 3° neutral dead zone. Bend or lower the upper body to duck; deeper bows suppress forward travel. Feet animate in the game.
- Slip left/right immediately. Against an opponent's left punch, slip right; against their right, slip left. Hold the same lean continuously for two seconds to circle in that direction. Neutral or reversal resets the hold. The server also verifies the duration.
- Straight punches, hooks, uppercuts and short forearm jabs are recognized. Full normalized shoulder–elbow and elbow–wrist directions drive the arms continuously, without compressing lateral reach, stretching bone lengths, or forcing each scoring event into a preset arm animation. Retract to a neutral position and settle for 180 ms before another strike. Retraction itself is never classified as a strike; held extensions and jitter do not repeat. Temporary tracking loss requires neutral recovery/calibration. A separate camera-session strike counter survives detector recalibration.
- Hold both elbows near shoulder height for three seconds to guard. Armor is consumed only by a blocked impact. Slips/ducks and movement cost no armor. Uppercuts can counter a deep duck.
- The bag is at the arena center in Training. Friend mode waits in the invitation lobby and loads a two-fighter arena after both cameras are ready. Hits show projected damage numbers and bag motion. Both players see HP/armor and match damage feedback.
- Drag to orbit, scroll/pinch to zoom, or select Ringside, Follow fighter, Overhead and Full screen. Ringside tracks the line between the fighters; Follow uses the current user's fighter.
- Matches remain best of three (first to two knockouts), with a five-second break, fresh HP/armor each round and one trophy recorded on the winner's profile. The clock counts active round time. Instructions are also available in Thai/English under the arena.

## Mechanics and compatibility

New rooms use rules version 4. Server-owned planar coordinates constrain movement to the octagon, normalize diagonal speed and separate overlapping fighters. Opponent-facing movement combines radial approach/retreat with tangential circling. Stale controls expire after 650 ms. Strikes have a 180 ms windup and then resolve range, captured aim direction, fresh directional slip/duck, guard and HP in that order. Recent strike IDs and event sequence numbers prevent repeat damage. Finishing a match clears pending impacts. Existing version 2/3 rooms retain their original server rules; no account/profile migration is needed.

The browser interpolates snapshots and animates the approved skeleton in the shared renderer. Only normalized arm vectors and control values are sent; camera frames remain local. This is a casual HTTP-synchronized game with explicit evasion rules, not a full rigid-body martial arts simulation. Device tracking quality and connection latency still affect responsiveness.

## Reference study

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

The championship browser test runs two accounts at 1280 px and 390 px with real browser fake-camera streams and synthetic upper-body landmarks. It covers forward/back movement, crouch/stand, torso bend, two-second circling without hips/legs, camera views/orbit/zoom, fullscreen and fallback, reduced motion, English/Thai, center bag damage, directional evasion, recoil suppression, a complete 2–1 match, per-round reset and one final trophy. Dedicated route/geometry cases cover timing, stale signals, boundaries/collision, guard, duck/uppercut, range, invalid controls and strike-ID replay. The avatar regression covers customization, save/reload and rotation.

Physical webcam accuracy has not been measured on the user's camera. The read-only deployment verifier checks the exact release revision/assets and exercises a shared scene with the public avatar assets without creating live accounts.

The current change is checked with root Python and installer/source tests, detector fixtures, the championship flow, and the natural-rig/control regressions above. The rig check measures full arm-chain reach, preserves short-jab extension during the impact envelope, verifies finite normalized skin weights, and exercises both saved avatar genders. Browser animation assertions wait for rendered state rather than assuming that a software renderer completes an animation on a fixed wall-clock frame.

Review images: [ringside](ringside.png), [solo practice](practice.png), [overhead](overhead.png), [mobile](mobile.png).
