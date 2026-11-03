# Rule 11: defensive X challenge

X retains its 4 m activation range and 180 real-second cooldown. Both fighters freeze for a 10-second defender challenge. HP at activation selects eight 1.25 s targets for HP >= 50%, or ten targets ramping from 1.55 s to 0.45 s below 50%. Positions are randomized on a bounded 3×3 grid with no immediate repeated position. The client receives the schedule but the server validates defender identity, special ID, target ID and wall-clock window; no client timestamp/count/damage is accepted. This is server validation, not an anti-aimbot claim.

All targets and no stray click evade X. Misses still run the full challenge; after a 180 ms delivery grace they enter the existing 6.2-second cinematic. Its one impact deals 50% defender maximum HP, capped by remaining HP. A lethal hit finishes the cinematic before the existing launched knockdown and round/reward flow. Bot defenders use server-owned reaction delays; accelerated low-HP targets can beat them. Cooldown begins at X activation regardless of outcome.

Challenge resolution runs before the shared combat-clock sync. This preserves exact paused time on success and composes with V. Stamina does not regenerate through the pause. Existing rooms below rule 11 retain their mechanics; new rooms and rematches use rule 11. No data migration or replacement of avatars, profiles, workout history or account logic.

Performance: adaptive remote interpolation (80–220 ms), unchanged bounded local preview, adaptive render pixel ratio (0.85–1.5), reuse of vitals DOM nodes and no WebGL rendering during the challenge. All combat outcomes remain server-owned. Network delays beyond the delivery grace can still cause a missed target; no fixed-FPS or latency guarantee.

Local verification uses disposable databases and synthetic accounts. Production verification is read-only via `tests/verify_live_boxing.py`. See the project-root `design-qa.md` and included screenshots for interaction and visual evidence.
