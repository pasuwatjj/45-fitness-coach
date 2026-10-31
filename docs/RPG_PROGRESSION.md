# Verified-workout RPG muscle progression

The approved CC0 Quaternius model, topology, textures, face options, hairstyles,
clothing, and rotation are retained. The original asset files are unchanged.

New profiles without verified workouts start at LV 1 / 0 EXP with minimal muscle
bulk and softened muscle shading. Appearance edits/recreation do not reset earned
progress. Existing verified history continues to count; no accounts, history, VIP
status, rewards, or profile measurements are deleted or rewritten.

## Authoritative credit

`character.growth` derives totals from saved `workout_sets` joined to a matching
`quality_sets` record by set ID, profile, and exercise. Only the smaller of their
positive saved rep counts is eligible. These quality records are written by the
server after completed accepted reps are saved; rejected or unverified attempts,
missing quality records, mismatched records, unsaved sets, and client-supplied EXP
cannot award growth. A verification-write failure leaves the set pending until a
successful retry. Unique set IDs prevent double credit. Legacy verified records
without difficulty retain the beginner rate. Historical records without verification
remain in workout history/rewards but do not qualify for avatar growth.

The existing economy is unchanged: beginner 10, pro 100, expert 1,000 EXP per accepted
rep; LV costs 10, 100, 1,000, ... with carry-over. Each exercise credits its catalog
primary group (arms, chest, back, legs, shoulders). Arm-side totals are capped by
eligible reps. Left and right arm development remains independent.

## Rendering and UI

Smooth regional deformations shrink undeveloped regions of the existing mesh;
maximum development restores its exact approved geometry. Detail is independently
blended between softened and authored color/normal shading in each region. Garments
use the same deformation, so their fit follows development. Face/head geometry is
excluded from muscle deformation. Height and weight independently control overall
height/fullness; no body/muscularity sliders or muscle-mass estimates were added.
This is RPG progress, not a measurement of biological muscle gain.

After a successfully saved workout, open character editors refresh server-derived
EXP and geometry while preserving unsaved appearance edits. Out-of-order refreshes
and late model loads cannot overwrite newer state. Both editor variants show the
existing per-group EXP/LV panel. Live exercise tracking retains its existing renderer.

## Validation

- 300 repository regression tests and 24 focused avatar/installer tests pass.
- Existing EXP boundary, retry, concurrency, ownership, frozen-difficulty, client
  injection, and mixed-difficulty tests pass with verified-workout fixtures.
- 12 old regression failures reproduced on untouched PR commit `3b29220`. Assertions
  were reconciled with already-existing v35 immediate-reference/manual-rest behavior,
  independent static-file versions, and default appearance validation. The hand-failure
  fixture now supplies a visible body so it actually exercises the hand detector.
  Application calibration, rest, cardio, and hand-tracking behavior was not changed.
- Node checks: all original model/clothing vertices finite, bounded independent group
  and arm-side deformation, monotone development, unchanged head and maximum geometry;
  existing 27 geometry variants and 102 garment coverage raycasts pass.
- Chromium software WebGL, 390px DPR 2/touch and 1280px: novice/developed renders,
  same-appearance pixel differences after verified credit, no unverified credit,
  independent group/side levels, refresh preserving unsaved cosmetics, save/reload,
  facial changes, clothing/hair/colors, keyboard/touch rotation, loaded visibility,
  navigation, cold gender races, teardown, and asset failure fallback.
- All synthetic workouts and test accounts use a disposable local database. Live
  release verification uses GET-only checks and synthetic in-browser preview levels;
  it never awards production EXP or modifies existing users.
- Physical mobile hardware, real-camera accuracy, and physiological muscle growth
  are not certified by software-browser tests.

## Review images

- [Desktop beginner](progression-review/1280-beginner.png)
- [Desktop developed](progression-review/1280-developed.png)
- [Only right arm developed](progression-review/1280-right-arm.png)
- [Mobile beginner](progression-review/390-beginner.png)
- [Mobile developed](progression-review/390-developed.png)

## Deployment verification

The existing Render service auto-deploys GitHub main. `/status` exposes the nonsecret
`revision` from `RENDER_GIT_COMMIT` and `avatar_progression: verified-muscle-v1` for
read-only rollout confirmation. Verify the merged revision plus live renderer/assets
and visible novice/developed previews before reporting deployment success. No new
service, data migration, or production seed routine is part of this change.
