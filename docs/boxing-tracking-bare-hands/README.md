# Camera attack mapping, bare hands and one-second travel

Camera-detected straight punches and short jabs now trigger same-side hooks. A detected punch during a calibrated torso lean or dip triggers an uppercut; leaning alone does not create a strike. Existing natural hooks/uppercuts, return-to-ready gating, side selection and cooldown remain. The struck arm blends into the requested hook/uppercut and returns to measured joints, while camera input still controls movement and the other arm. Keyboard input remains disabled in camera rooms.

The approved avatar's complete skinned hands and original articulated finger pose replace the procedural MMA overlay. No hand triangles are hidden and no replacement glove or fingertip meshes are added. Shared profile appearance and proportions remain unchanged.

Shared uppercut motion now loads the knees and torso more deeply before rising into the strike in both computer and camera modes. This visual motion does not grant additional server-side evasion beyond the user's measured controls.

Camera movement begins after a one-second continuous lean in all four directions, including diagonal combinations. Detector counters, server lateral hold and Thai/English instructions agree. Neutral recovery, early reversal, stale-frame stop and immediate direction changes after travel starts remain covered.

Validation:

- 55 boxing server tests (54 existing plus the new one-second boundary test); 25 installer/manifest tests.
- Node pose/computer suites: 999/1,000 ms boundary, straight-to-hook, bilateral leaning/dipping uppercuts, no lean-only/held/retraction bonus strikes, yaw/head isolation, key rules and smooth motion.
- Real male/female mesh, elbow, contact, natural pose and computer rig browser suites. Uppercut load lowers the head over 15 cm and increases knee flexion; both sides rise over 40 cm from chamber in both control modes. Actual hook arm geometry is bent for a straight camera input.
- Camera-only end-to-end browser regression in Thai/English: new punch mapping, movement, navigation, two-client three-round 2–1 match, knockdown/recovery and exactly one belt. Uses a synthetic landmark stream through the actual browser control loop; it is not a physical camera accuracy study.
- Local read-only release verifier passed; exact live deployment verification is recorded in the PR.
