# Counter, Time Shift and Ruesi Bod Ya

The boxing update follows the user's final specifications: matching punches rebound with zero damage, V lasts one minute with a two-minute cooldown, and X performs the reference Ruesi Bod Ya sequence with **one normal right-arm damage hit** and a **three-minute cooldown**. The existing characters, accounts, rewards and exercise/profile features remain in use.

## Mechanics

- Counter is server-authoritative in computer and tracking rooms. Opposing pending punches must use the same hand and type (straight/hook/uppercut), be within 1.65 m, face one another, and have contact times within 120 ms of combat time. Evasion, out-of-range swings, different attacks, kicks and already-landed hits do not qualify. Both attacks are consumed together without HP or armor damage. Clients retract the striking arms and show `Counter · 0`.
- V slows both players to 40% for 60 real seconds. Its 120-second cooldown starts at activation. The arena shows both players' cooldowns and the shared effect countdown. A native SVG clock appears once with a single grayscale pulse; reduced-motion/effects-off preferences remove the animated pulse. There is no repeated strobe or image overlay.
- X can start within 4 m during a round. Its 6.2-second server-timed cinematic runs through approach, left-foot/right-thigh step, right-foot/shoulder climb, left-hand neck hold, and right elbow to the crown. The receiving fighter lowers into a staggered stance. The original rig uses fixed-length limb solving, followed by a return to the original fighting positions.
- X applies the current right-arm damage once at 4.1 seconds, directly to HP; it does not consume armor. Repeated packets cannot apply another hit. Combat timers and both players' controls pause during the cinematic; real-time V/X cooldowns continue. A lethal X enters the existing round/end/reward flow after the cinematic, without replaying the generic finisher.
- X defaults to `X`; right lean moves to `B`. Existing custom key mappings are preserved and new bindings select a free key where necessary. The in-arena V/X buttons also work on touchscreens and in fullscreen. The guide and tooltips describe the final durations, range and damage.

## Visual/interaction review

1. **Counter / passed:** two actual keyboard clients received the same zero-damage event. Both HP/armor values stayed intact and both saw feedback. [Screenshot](counter.png).
2. **HUD / passed:** enlarged native HP bars, independent V/X cooldowns, and in-arena ability buttons remain readable on desktop, 390 px mobile and fullscreen. A discovered overlap with Rematch was fixed by hiding abilities on terminal matches. [Mobile screenshot](mobile.png).
3. **Reference pose / passed:** the receiver crouches; the attacker places the left foot on the right thigh and right foot on the shoulder. Stable prepare/impact frames keep both contact errors under 3 cm in the male/female fixture; impact elbow-to-crown distance is under 8 cm. [Prepare](ruesi-prepare.png), [elbow](ruesi-elbow.png), [measurements](rig-measurements.json).
4. **Recovery / passed:** control resumes after X, damage is applied only once, and skill/round/cooldown states survive both-player updates. Reduced motion removes the V pulse, and renderer/overlay cleanup was exercised.

The pose screenshots are deterministic renderer fixtures using the shipped models and choreography, not photos or captured human motion. Separate authenticated two-player browser tests exercise real X and V input. This is stylized game choreography, not a claim of physically simulated human contact or universal device frame rate.

## Validation

- 119 Python tests: legacy boxing, Counter, X, V, guards, cage, bots, custom rooms, finale, training and installer.
- Node: computer controls/key migration, camera pose mapping, playback and training flow.
- Browser: `qa_boxing_counter.py`, `qa_boxing_special.py`, `qa_boxing_special_scene.py`, `qa_boxing_skill_rematch.py`, `qa_boxing_evade_slow.py`.
- Read-only release smoke checks exact revision, public asset bytes, avatar scenes, reference-pose contacts, key defaults and existing native homepage UI. Production accounts are not used for synthetic tests.

Figma was requested, but its Starter-plan MCP call quota rejected the read attempt in this task. No new Figma canvas changes are claimed. Visual checks use captured running-browser screenshots following the Product Design review workflow.
