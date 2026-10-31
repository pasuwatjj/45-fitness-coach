# Avatar model research and provenance

The Quaternius candidate below is now approved and retained. The current RPG muscle
progression implementation and deployment checks are documented in
[RPG_PROGRESSION.md](RPG_PROGRESSION.md). The following is the earlier model-selection
record; its draft/no-deployment status describes that earlier research step.

## Resumed work, 2026-10-31

Inspected Draft PR #3 and the clean `research/avatar-model-upgrade` checkout at
`cfcbc6e11d92466ad50f48bc53f2524af032de0f` before changes. Continued that work; no
replacement PR, merge, production request, migration, or production database write.

## Official download and license

The previously blocked official Standard download **now succeeds (HTTP 200)** through
the environment's enforced allowlist. No additional domain is missing in this run.

- Catalog: https://quaternius.com/packs/universalbasecharacters.html
- Official distribution: https://quaternius.itch.io/universal-base-characters
- Free Standard upload ID: `15861669`
- Resolved asset host: `itchio-mirror.cb031a832f44726753d6267436f3b414.r2.cloudflarestorage.com`
- Archive: 128,968,391 bytes; SHA-256 `fdbf1804c90dfc1ea03e992bff7da2dfd1a79318e13270a660180f9308455f40`
- Included `License_Standard.txt` explicitly dedicates the Standard models to CC0 1.0.
  Its verbatim copy is `static/models/quaternius/LICENSE.txt`. Browser redistribution
  and these derivatives are permitted. No paid, Daz, or unlicensed reference assets
  were copied. Branding/support links in the license are retained.

## What is actually in the archive

The male and female Superhero models have roughly 7.3k vertices each, articulated
humanoid rigs, eye and eyebrow meshes, and authored color/normal textures. There are
separate hairstyle assets. **There are no facial/body morph targets or interchangeable
clothing meshes in this free archive.** Two relative texture references use incorrect
`_png.png` names; the conversion repairs these against files included in the archive.

| Candidate | Evidence and decision |
| --- | --- |
| Quaternius Universal Base Characters Standard | Download and included CC0 license verified. Integrated as a **stylized editor candidate**, with authored muscle detail and better head/body proportions than the procedural renderer. Source has pronounced superhero anatomy; it does not establish photorealistic or population-representative proportions. |
| MakeHuman / MPFB | Still an alternative for a broader facial/body morph pipeline. Official bundled assets/output are CC0; application code is AGPL and third-party assets need individual license checks. No exported MakeHuman model is integrated or visually qualified in this PR. |
| Daz Jaheem HD / Phx Han HD; 3dmodels.org reference | Visual references only. Browser redistribution rights have not been verified; no assets used. |

MakeHuman sources: https://github.com/makehumancommunity/makehuman/blob/master/LICENSE.md,
https://static.makehumancommunity.org/about/license.html,
https://static.makehumancommunity.org/mpfb/docs/assets.html.

## Integration and limits

- Both character editor interfaces use locally served derivative meshes and textures.
  No third-party model service, external asset request, or new runtime dependency.
- Saved profile height/weight drive approximate fullness and height, with a neutral
  default if missing. Manual body/muscularity sliders remain removed. Height/weight
  cannot determine muscle mass or a person's exact shape; sculpted muscle detail is
  an artistic property of this candidate, not a measurement inferred from BMI.
- Existing appearance keys, accounts, progression, and data storage remain intact.
  Face/eye/nose options use modest, original regional vertex adjustments, **not
  verified artist-authored morphs**. Three authored hairstyles plus procedural curls
  and ponytail provide the existing selection keys. The `bob` key is retained for
  compatibility and labeled Long for the imported hairstyle.
- Sports top, tank, tee and shorts are generated fitted shells from the body. Clipped
  triangle boundaries avoid jagged hems, and female sportswear includes straps. These
  are close-fitting garments, not authored loose clothing or cloth simulation. The
  heavy-body candidate still looks strongly muscular; these limits need visual review.
- Live exercise pose tracking retains its existing articulated renderer. The new
  editor assets are baked to a relaxed pose. **The imported model is not yet a unified
  replacement for the live exercise avatar.** The original live renderer and its
  coverage/geometry checks are preserved.
- Async loads use a generation guard, preserve a visible procedural fallback on
  failure, and dispose textures/geometry at teardown. Gender switches and pending
  teardown cannot install a stale model.
- All model files total about 8.1 MiB before HTTP compression. Textures are at most
  1024px (512px for hair). Physical-device GPU memory, thermal behavior, and sustained FPS remain
  unmeasured. Do not equate software-WebGL viewport tests with phone performance.

## Reproduction

Place the official Standard archive at `work/quaternius.zip` and extract it into
`work/quaternius/`. From the repository root:

```
blender -b --python tools/export_quaternius.py
.venv/bin/python tools/prepare_quaternius_textures.py
```

Blender 4.3.2 bakes the arm pose, exports positions/normals/UVs and clipped clothing
surfaces; Pillow downsizes the included textures. The scripts use no application data.
The cumulative installer manifest includes the new assets and recognizes the prior
branch hashes without weakening protection for unrelated local edits.

## Validation and screenshots

Use a disposable local database, e.g. `FITNESS_DATA_PATH=$PWD/work/qa.db`, with the
Flask app on `127.0.0.1:5055`. Never point QA scripts at production.

- 24 Python unit/installer tests pass.
- Existing articulated renderer: 27 geometry variants and 102 clothing coverage
  raycasts pass (these checks do not qualify the new static meshes).
- `tests/qa_imported_avatar.py`: Chromium software WebGL at 390px (DPR 2, touch)
  and 1280px. Male 175cm/76kg, female 165cm/60kg, male 175cm/105kg; keyboard and
  real touch/mouse rotation with pixel comparisons; face controls alter pixels;
  clothing/hair selection, saved dimensions, reload persistence, visible model after
  loading, and navigation/re-entry. No page errors.
- `tests/qa_imported_lifecycle.py`: alternate studio clothing/hair save/reopen,
  post-save edits, saved eye/hair colors, front/back screenshots, cold gender-switch race, pending-load teardown, and visible
  fallback after a deliberately failed model request.
- Screenshots in `docs/avatar-review/` are actual local renders, not concept images.
  Review front, side and back garment fit and the stylized body proportions before
  approving this candidate. PR remains draft; no merge or deployment approval.

Review images:

- [Desktop male, 175cm / 76kg](avatar-review/1280-male-76-front.png)
- [Mobile female, 165cm / 60kg](avatar-review/390-female-60-front.png)
- [Desktop fuller build, 175cm / 105kg](avatar-review/1280-male-105-front.png)
- [Female side view](avatar-review/390-female-60-side.png)
- [Tank back view](avatar-review/1280-tank-back.png)
- [Desktop studio](avatar-review/1280-studio.png)
- [Mobile studio](avatar-review/390-studio.png)
