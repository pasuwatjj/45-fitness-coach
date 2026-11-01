# Computer boxing motion and animated fighter lobby

The supplied Hajime no Ippo video was reviewed as a 16-frame contact sheet, alongside the supplied Ultimate MMA kick stills. The implementation uses original procedural choreography on the existing Quaternius rig: a bent-knee stance with tucked chin, hip-led punches, chamber/extension/recoil/replant kicks, and a lowered dash. No game models or animation clips were imported.

Computer punches reach extension around 180 ms; kicks extend around 280 ms and recover over 760 ms. Support ankles stay planted and limbs keep their original lengths. Alternating three distinct punch presses within the combination timing ends in a hook. Held keys do not generate additional strikes. F raises guard immediately, C crouches, and Space plus WASD performs a directional ducking dash. Guard, crouch and strikes retain remappable bindings. High kicks can be ducked; uppercuts counter a duck. The server enforces kick recovery, stops movement during committed kicks, and prevents dashes from crossing opponents. Remote strikes start at the elapsed server timestamp instead of restarting on packet receipt.

Tracking retains measured arm/body motion and its existing guard/movement calibration. The camera and keyboard callbacks are separated. New rooms require the matching input-source declaration; the server rejects missing/mismatched sources, keyboard strafing, kicks and dashes in Tracking. Both guests inherit the host's room mode. This prevents mixing controls in the shipped client. Source declarations are client-supplied, so this is not proof of a physical camera or protection against a modified client that fabricates camera data. Existing server sequencing, cooldowns, range checks and duplicate-strike prevention remain authoritative.

The lobby has gently changing warm/cool light, an actual ground-plane contact shadow, and a repeating footwork/jab/cross/hook warm-up. Preview rendering is capped at 24 fps, stops drawing offscreen or in a hidden tab, and freezes with reduced motion. The scene and its GPU resources are disposed when entering a game. Profile levels, saved appearance, the generated background, and the disabled Bot entry remain intact.

Validation uses disposable local databases. See the committed browser fixtures and `measurements.json`: male/female, left/right kicks reach 1.54–1.59 normalized world height with about 99.9% fixed-length leg extension and support-ankle drift below 0.000001 world units in deterministic isolated poses. These geometric checks are not a claim of biomechanical simulation. Existing timed planar combat ranges remain unchanged.

- `tests/test_boxing_computer.cjs`: input edges, remapping, distinct combination presses, kick recovery, no baseline evasion, disabled keyboard mode and continuous phase curves.
- `test_boxing_cage.py`: source/mode rejection, instant computer guard, tracking guard, dash duck/uppercut counter, high-kick duck, recovery and planted movement.
- `tests/qa_boxing_computer_rig.py`: real male/female rigs, strike phases, full extension, dash posture, tracking isolation, contact and recovery.
- `tests/qa_boxing_lobby.py`: desktop/mobile menu, shared mode, settings, keyboard practice/match, immediate block and cleanup.
- `tests/qa_boxing_championship.py`: all gameplay keys inactive in camera mode; camera movement, punches, rounds and championship regression.
- `tests/verify_live_boxing.py`: GET-only exact-revision/asset verification, real rigs, animated lobby, reduced-motion pause, settings and mode selection.

Screenshots: [lobby](lobby-desktop.png), [mobile](lobby-mobile.png), [stance](stance-0.png), [punch](punch-0.png), [male kick](kick-0.png), [female kick](kick-1.png), [dash](dash-0.png).
