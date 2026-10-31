# Boxing

Private, casual matches between accepted friends. Invitations are stored in existing friend chat and open the Boxing room list. A saved avatar and an owned profile are required. Appearance, muscle development and each arm's verified progression are snapshotted for the match; no workout rewards or account balances are changed.

Each fighter starts with 10 HP and 10 armor units. A punch deals the attacking arm's profile level. Blocking consumes one armor and prevents the whole hit. At zero armor, blocking no longer prevents HP damage. A new lean gesture consumes one armor for a 450ms dodge window; holding the lean does not repeatedly consume armor or grant permanent immunity. Both players ready up before a five-second countdown. Leaving forfeits; a 20-second heartbeat loss ends an active match. Invitations expire after two minutes; rooms expire after 30 minutes.

The server serializes updates in SQLite and enforces profile ownership, friendship, membership, cooldowns and monotonic event sequences. Matches persist in one additive table. Gesture detection is client-side and is not competitive anti-cheat. No camera frames or landmarks are sent to the opponent or game server. Only discrete actions are exchanged.

The control camera starts only after a button press. Self-preview defaults to hidden and has a separate toggle. Leaving the page releases the stream and renderer. Detection uses confident nose/shoulder/elbow/wrist landmarks; it calibrates neutral head position and normalizes relative movement by shoulder width, combines world-depth changes for leaning, and recognizes punches from bent-to-extended arm transitions. Camera angle, occlusion and lighting affect accuracy. It does not measure physical punch force. Real-human camera accuracy needs testing on target devices; automated tests use deterministic landmarks and a browser fake MediaStream.

Sources consulted:
- [MediaPipe Web Pose Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/web_js): landmarks, confidence, world coordinates and worker-based video inference.
- [Google's browser sample](https://github.com/google-ai-edge/mediapipe-samples-web/blob/main/src/tasks/pose-landmarker.ts): browser inference integration.

The existing local MediaPipe runtime and Quaternius renderer are reused. Arena artwork was generated for this project; no Street Fighter characters or assets are included.
