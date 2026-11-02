# Loy Krathong release

The homepage now uses a candlelit midnight river and cute fitness characters, with a cream/forest alternate palette. Three illustrated cards lead into strength, cardio and boxing. The existing profile and account navigation stays available. Both themes use the golden lightning click effect and respect reduced-motion preferences.

Fight Club has a new gym banner, stronger mode selection, teal/gold panels and arena controls. Computer-controlled steps filter instantaneous speed and keep the supporting foot planted on the mat. This is a rendering change; collision positions, match authority, damage, rewards, bots and account persistence keep their existing owners.

The production WebP assets total approximately 690 KB. Lightning uses Bootstrap Icons under the included MIT license. Figma image previews are compressed; the website uses the full resolution optimized assets.

Validation commands:

```sh
BOXING_TEST_ORIGIN=http://127.0.0.1:5082 .venv/bin/python tests/qa_festival.py
BOXING_TEST_ORIGIN=http://127.0.0.1:5082 .venv/bin/python tests/qa_boxing_lobby.py
BOXING_TEST_ORIGIN=http://127.0.0.1:5082 .venv/bin/python tests/qa_boxing_finale_scene.py
BOXING_TEST_ORIGIN=http://127.0.0.1:5082 .venv/bin/python tests/qa_boxing_flow_training.py
BOXING_TEST_ORIGIN=http://127.0.0.1:5082 BOXING_TEST_DB=/tmp/festival-qa.db .venv/bin/python tests/qa_boxing_finale.py
node tests/test_boxing_computer.cjs
node tests/test_boxing_flow.cjs
node tests/test_boxing_pose.cjs
.venv/bin/python -m unittest discover -s tests -p test_installer.py
```

Read-only deployment check: `.venv/bin/python tests/verify_live_boxing.py <merged-revision>`.

See [design QA](../../design-qa.md) for screenshots and the editable Figma file. Browser testing uses Chromium software rendering and does not establish FPS or network latency on the user's hardware.

All commands above passed. The first finale run overlapped another software-rendered browser suite and missed its short active-cinematic assertion; an isolated rerun passed friend, easy-bot and hard-bot ceremonies. Deterministic impact/framing checks also passed. Supporting-foot maximum displacement between samples sharing a stance was below 1e-14 world units at both update rates (53 / 111 samples), with stop and camera-tracking release verified.
