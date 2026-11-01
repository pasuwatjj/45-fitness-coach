# Elbow, uppercut and training-room lobby correction

The guard previously rotated the upper arm and forearm independently in world space. Near the folded guard this added an axial half-turn, pinching the original elbow mesh. Forearms now bend in their rotated parent's frame in tracked/computer poses, contact IK and round presentation. Fist pronation happens at the glove attachment. The shared profile mesh, proportions and measured tracking endpoints are preserved.

Space + A/D now throws left/right uppercuts; Space + W throws the forward right uppercut. The animation chambers beside the ribs, rises with hip/knee drive and returns to guard. Alternating Q/E combinations retain their hook finisher. Both languages describe the revised mapping.

The menu uses one 3D training room with a tiled floor, training mat, live shadows, ring, lockers, lighting and overhead bag support. Individual interlocking chain links attach the swinging bag to a fixed support. The saved fighter and room share a camera and ground plane. Mobile places progression below the scene; preview is capped at 24 fps, pauses offscreen/hidden, respects reduced motion, and releases geometry/materials/shadow resources on exit.

## Validation

- 54 boxing server tests: room ownership/mode, invitations, sequences, strikes, guards, rounds and disconnects.
- 25 installer/manifest tests, JavaScript computer and pose suites.
- `qa_boxing_elbows.py`: actual triangle areas on both real male/female elbow surfaces, idle and all guard variants; bilateral uppercut chamber/rise/recovery. The old release fails the regression (minimum area ratio 0.094, median 0.869); corrected male idle is 0.326/0.953 and female 0.221/0.984. This is a targeted collapse regression, not a universal mesh-quality guarantee.
- `qa_boxing_computer_rig.py`, `qa_boxing_natural.py`, `qa_boxing_contacts.py`: real assets, full/short punches, fixed lengths, kick/foot behavior, camera pose isolation and contacts.
- `qa_boxing_lobby.py`: two isolated browser accounts; invitation/acceptance and shared input mode, live damage/guard sync, movement/dash, repeated practice navigation, live-match navigation, camera lock, key remapping, desktop/mobile and cleanup. No new matching failure was reproduced; matchmaking backend unchanged. Network conditions on users' devices can differ.
- Read-only local release verifier: exact assets/template, actual scene, knockdown/belt, animated chained-bag lobby, reduced motion and controls. Deployment verification is recorded in the PR.

Before/after elbow screenshots use the same high camera angle as the report. Screenshots use disposable local fixtures, never production accounts.
