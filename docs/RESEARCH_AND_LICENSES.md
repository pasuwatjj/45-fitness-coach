# Research & licensing — V44

Checked 30 October 2026. Reference images supplied by the user guide the general stylized human proportions, face features and range of body fullness. No mesh, texture, or screenshot from 3DModels.org is redistributed.

- Three.js official GitHub: https://github.com/mrdoob/three.js — rendering, meshes, materials, transforms and articulated groups. Bundled npm distribution `three@0.160.1`, a deliberately pinned legacy non-module build for the existing script-based Flask frontend. This is not claimed to be the latest version. It emits a deprecation notice; a future module migration should update all script loading together.
- Three.js Mesh documentation: https://threejs.org/docs/pages/Mesh.html
- Three.js SkinnedMesh documentation: https://threejs.org/docs/pages/SkinnedMesh.html — reviewed as a potential rigging route. This implementation instead uses hierarchical articulated groups and procedurally rebuilt contours; it does not claim to load a skinned GLB or use authored morph targets.
- Three.js license: https://github.com/mrdoob/three.js/blob/r160/LICENSE — bundled copy in `static/vendor/THREE-LICENSE.txt`.
- 2024 Adult Compendium: https://pacompendium.com/adult-compendium/ — adult reference age range 19–59, not individual calorimetry.
- Conditioning exercise MET table: https://pacompendium.com/conditioning-exercise/ — codes 02054, 02020, 02030 and 02022. Mapping upper-body cardio to general light/moderate calisthenics is an implementation assumption, not a separate measured Compendium activity.
- MET definition: https://pacompendium.com/ — 1 MET convention is 3.5 ml oxygen/kg/min. The gross-energy approximation assumes 5 kcal per litre of oxygen; active energy subtracts 1 MET. Neither number is a personal resting metabolic-rate measurement.

New character meshes and application code in this update are generated specifically for this project. The existing project's license is preserved; this package does not relicense pre-existing app code. The MediaPipe model and cumulative V42 files are inherited from the supplied update, not newly downloaded assets in this change.
