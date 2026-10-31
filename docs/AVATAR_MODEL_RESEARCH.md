# Avatar upgrade research — incomplete, not deployment approval

Official sources inspected on 2026-10-31:

| Candidate | Appearance evidence | Compatibility and customization | License | Decision |
| --- | --- | --- | --- | --- |
| Quaternius Universal Base Characters | Inspected official Standard preview: anatomically defined male/female bodies, stylized faces and hair; less realistic skin than the supplied Daz references | Catalog advertises glTF, humanoid rig and about 13k triangles. Free Standard preview specifies two bodies and five hairstyles. Facial/body morph targets and clothing replacement are NOT verified in downloaded files. | Official catalog and Standard preview state CC0 | Promising stylized candidate; not selected pending actual asset inspection |
| MakeHuman / MPFB | No exported candidate rendered yet | Bundled targets and clothing documented; export requires a pipeline and actual verification of retained morphs, rig and clothing fit | Official MakeHuman LICENSE.md specifies CC0 bundled assets/output, AGPL application code; third-party assets have independent terms | Candidate pipeline, not a verified ready-to-use GLB |
| Daz Jaheem HD / Phx Han HD | User-supplied screenshots show the desired detailed anatomy and realistic skin | Actual model, mobile cost, export, morph and clothing support unverified | No asset-specific browser redistribution permission verified | Reference only; no asset copied |
| 3dmodels.org Fat Man | User-supplied screenshot illustrates fuller proportions | Rig, morphs and topology unverified | No asset-specific redistribution license verified | Reference only; no asset copied |

Sources:
- https://quaternius.com/packs/universalbasecharacters.html
- https://quaternius.com/assets/images/fullres/universalbasecharacters/standard.jpg
- https://github.com/makehumancommunity/makehuman/blob/master/LICENSE.md
- https://static.makehumancommunity.org/about/license.html
- https://static.makehumancommunity.org/mpfb/docs/assets.html

The Quaternius catalog and itch.io download page are now accessible, as is GitHub API access. The free Standard archive resolves to itchio-mirror.cb031a832f44726753d6267436f3b414.r2.cloudflarestorage.com, which the proxy denies. This exact host has been added to the environment draft for review. No replacement model is selected or integrated. No claim of tested facial morphs, clothing fit, browser performance or visual equivalence is made.

Independent implementation removes manual muscularity controls from both existing creator interfaces. Height/weight continue to guide approximate fullness; muscle definition stays neutral and independent of BMI. Legacy appearance records and progression data are preserved. Missing measurements use a default and the studio prompts for completion. The existing renderer remains in place pending model qualification.

Before approval: inspect actual male/female assets, verify asset license and available morph/clothing data, render several body types, test desktop/mobile rotation, save/reload, clothing intersections and performance. Current automated checks do not establish these visual requirements.

Current validation: 24 Python tests pass. Chromium with software WebGL passed editing/save/reload at 390px and 1280px for 175cm/58kg, 175cm/105kg and 195cm/95kg. This is viewport emulation, not physical-device performance validation. Screenshot inspection of the existing renderer shows visible shirt shoulder gaps and inadequate visual quality relative to the references. Rotation input was exercised but no automated pixel comparison was performed in this run. No deployment approval.
