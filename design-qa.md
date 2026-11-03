# X defensive aim and restored exercise card — Product Design QA

final result: passed

## Source and intent

The user supplied an aim-trainer reference (navy grid, orange/white circular targets and central timer), an exercise-category card screenshot, and the original exercise portrait already in this repository. They explicitly requested native UI, a frozen grayscale arena, and a functional defensive challenge rather than a static image. This is a new interaction, not a pixel clone of the image-search browser chrome. No Figma destination was supplied or modified.

Source visual truth: the supplied chat references; `static/images/jeff/page-31.jpg` (720 × 1280); and `docs/winter-home/home-power-1440.png`, the previously accepted winter homepage at a 1440 × 1000 CSS viewport, DPR 1. The winter homepage source and implementation are both Thai, guest, dark theme; full-page heights differ intentionally because the restored photo card spans the grid.

## Browser evidence and comparisons

- Full-view source/implementation comparison: `docs/boxing-aim/comparison-home.png` (1250 × 1000). Both homepage captures displayed at the same width. Current source capture is `docs/boxing-aim/home-desktop.png` (1440 × 1873, viewport 1440 × 1000, DPR 1).
- Focused source-asset/implementation comparison: `docs/boxing-aim/comparison-photo.png` (1250 × 1000). Original portrait is shown alongside actual desktop and mobile card captures. Desktop card 1264 × 231; mobile card 366 × 221 at viewport 390 × 844, DPR 1. Portrait and card intentionally have different crops, clearly labeled in the comparison.
- New interaction: `docs/boxing-aim/aim-defender.png`, `aim-attacker.png`, `aim-evaded.png` (arena crops 1094 × 684, viewport 1200 × 950, DPR 1). Defender and spectator states share the same countdown but only the defender can click.
- Mobile interaction: `docs/boxing-aim/aim-mobile.png` (arena crop 352 × 441, viewport 390 × 950, DPR 1). No horizontal overflow; target remains 48 px. Desktop targets are 54 px.

## Findings and iteration

The first exercise-card render used a full-width crop that enlarged and cropped the subject's head. This was a P2 asset-quality issue. The image was constrained to a portrait region on the right with a 38% vertical crop, while the readable text stays on the left. The post-fix focused comparison above shows the face and upper body clearly at both sizes. The latest comparison has no remaining actionable P0/P1/P2 findings.

The aim trainer intentionally uses one target at a time, rather than the simultaneous static targets in the reference image, to make the user's continuous 10-second challenge unambiguous. The countdown, required total, misses, speed band and outcome text explain the rules. The grayscale applies to the arena behind the trainer; colored targets remain easy to find. The spectator sees the same sequence without interactive controls. Existing HP and skill HUDs stay around the arena edges; the challenge takes priority while combat input is frozen.

## Required visual surfaces

- **Typography:** Existing app stack retained; clear bold heading, tabular timer/counters, compact secondary copy. Thai/English and narrow screens checked. No browser-chrome imitation or reference-site labels.
- **Spacing/layout:** Trainer stays inside the arena/fullscreen container; responsive inset, bounded grid and 48–54 px targets. Original winter navigation and category actions remain usable. Wider exercise card intentionally restores prominence to workout learning.
- **Colors/tokens:** Navy glass, subtle grid and white/orange targets follow the supplied reference. Monochrome fighters communicate time stop. Success uses pale mint with explicit zero-damage text. Reduced-motion/global-effects settings suppress the decorative expanding clock.
- **Assets:** Existing human photograph restored; approved Quaternius fighters and the X choreography retained. Real targets are native interactive buttons as explicitly requested. No replacement AI image was generated.
- **Copy/content:** Rules say all targets for 10 seconds = evade; any miss = cinematic and 50% maximum HP damage. At exactly 50% HP the moderate schedule applies. X cooldown remains 180 seconds. Controls/help and bilingual labels updated.

## Interaction and regression evidence

- `tests/qa_boxing_aim.py`: two authenticated local players; defender-only native clicks, frozen renderer and transforms, grayscale, eight successful targets, zero-damage evade, 180-second cooldown, failed challenge, one 25 HP hit against 50 maximum HP, unchanged armor, original thigh/shoulder/elbow cinematic, mobile layout, clean exit and movement under alternating 40/180 ms response delays. No console errors.
- `test_boxing_aim.py`: nine focused server tests, including low-HP acceleration, exact 50% boundary, premature/duplicate/late/forged clicks, attacker exclusion, stray misses, V overlap, paused stamina, leave cancellation, bot reactions and KO after the cinematic.
- Full boxing Python regression run: 140 tests passed before adding the ninth focused bot case; all nine focused cases subsequently passed. Existing charged punch, Counter, stamina and reward rules are preserved.
- Node computer/flow regressions passed: input/remapping, charge, guard/dash, stamina, bounded interpolation/extrapolation, stale packets, cage bounds and training acknowledgments. Added bounded adaptive interpolation checks for uneven arrivals.
- `tests/qa_boxing_charge.py` passed: real left/right mouse remaps, full ×2 synchronized hit, tap, guard cancellation, impact effects, live bindings, mobile/fullscreen and reduced motion. Screenshot readback briefly interrupted charging in software WebGL; the test now waits for the server-confirmed full charge before release.
- Winter browser regression passed at 320/390/768/1440 px in both themes, including navigation, instructional media, reduced motion, pause persistence and effects settings. Local ambient-snow sample: about 60 fps. This is not a physical-device or multiplayer FPS guarantee.
- Rendering changes: stop WebGL drawing during aim; adapt pixel ratio between 0.85 and 1.5 under sustained load; update existing HP/armor/stamina elements instead of rebuilding the HUD on every response. Remote interpolation adapts within 80–220 ms; local input preview remains immediate and bounded.

## Checklist

- [x] Server-owned 10-second challenge and damage, with 180 ms packet-delivery grace.
- [x] Freeze / grayscale / clock cue and defender versus attacker UI.
- [x] Success resumes combat; failure plays the existing X cutscene once.
- [x] Restore exercise photograph and retain winter theme, tutorial media and account data.
- [x] Responsive and reduced-motion checks; actual browser screenshots reviewed.
- [x] Multiplayer uneven-delivery regression; no promise of fixed FPS across devices or networks.

No outstanding design blockers. Existing rule-10 rooms keep their earlier mechanics; create a new room for rule 11. Physical low-end mobile hardware and geographically distant internet connections were not tested.
