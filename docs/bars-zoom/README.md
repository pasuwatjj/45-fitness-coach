# Boxing vitals and avatar editor zoom

Boxing uses the same HP/armor meter component before and after a friend joins. The solo lobby shows the local character at 10 HP / 10 armor and a clearly labeled waiting slot. After acceptance, both cards show actual participant values. Cards stay at most 320 px wide and fit side by side on mobile.

The avatar editor supports 80–250% zoom using buttons, a slider, the mouse wheel, two-finger pinch, or + / - / 0 keys. Rotation remains available, outfit edits preserve the current zoom, and the reset button returns to 100%. This changes only the preview camera, not saved appearance or body measurements.

## Review evidence

- [Mobile solo lobby](390-solo-bars.png)
- [Desktop participants](1280-duel-bars.png)
- [Mobile zoom controls](390-zoom-controls.png)

Run `tests/qa_bars_zoom.py` against a disposable local server on port 5055. It creates local test accounts and verifies solo/invited/accepted HUD states, bounded cards, actual camera zoom, edit persistence, mouse/keyboard input, real CDP pinch input, overflow, and JavaScript errors at 390 and 1280 px. Never run it against production. `tests/verify_live_boxing.py REVISION` uses only GET requests to verify the deployed revision and exact assets.
