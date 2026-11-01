> Historical release notes. Current camera, body tracking, contact constraints and ten-second knockdown rules are documented in [boxing-cage](../boxing-cage/README.md).

# Boxing championship release

The camera controller accepts smaller backward lean, including head/torso disagreement and a perspective fallback when depth estimates barely change. Crouching lowers the body and bends the avatar's knees, then returns to standing with the player. Hand trajectories assist the nearest straight, hook or uppercut for either arm; retraction/cooldown prevents a held fist from repeatedly striking. Only posture/control vectors reach the other player; camera images remain local.

New invitations use best-of-three rules. A knockout wins one round; HP and armor reset to 10 after a five-second break, and the first player to win two rounds receives one trophy. The centered clock displays accumulated fighting time and pauses between rounds/at the end. Disconnects and leaving remain forfeits. Existing older matches keep their original rules. No destructive database migration is required.

The arena has original generated championship artwork, moving spotlights, light haze and small atmospheric sparks. Effects sit behind the fighters, respect reduced-motion and the existing effects-off preference, and do not require a canvas animation loop. HUD cards are transparent. Fullscreen uses the browser API with a CSS expanded-view fallback, Escape support and cleanup on leaving. The bag shows both floating damage and a persistent last-hit value. Boxing controls, tracking feedback, round labels, home entry and invitation presentation support Thai/English without translating player-authored names/messages.

## Verification

- 327 root unit tests and 25 tests under `tests/` pass; rounds, 2–1 comeback, HP/armor resets, timers, final trophy, posture validation and punch styles are covered.
- Pose fixtures cover gentle backwards tilt, depth disagreement, perspective fallback, cropped/occluded arms/hips, crouch/stand, both-handed straight/hook/uppercut, held-hand suppression and English labels.
- `tests/qa_boxing_championship.py` drives the actual camera loop in Chromium with fake streams and synthetic landmarks at 1280/390 px: forward/back, visible crouch and remote sync, assisted punches, bag damage, native/fallback fullscreen, transparent HUD, changing light transforms, reduced motion, English-only Boxing text, three rounds ending 2–1, break banners, clock freeze and exactly one trophy.
- Existing practice/two-player damage tests and avatar customize/save/reload/rotation regression pass.
- All accounts and matches are local fixtures. Physical cameras, framing and lighting can differ from these automated fixtures. Live verification is GET-only.

[Desktop, English](1280-championship.png) · [Mobile, Thai](390-championship.png). Motion was paused only while capturing screenshots.

The new arena image is original generated artwork inspired by the requested professional stadium setting, not copied from a stock preview.
