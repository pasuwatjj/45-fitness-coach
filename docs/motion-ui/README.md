# Native motion UI revision

The user requested the original exercise photograph, the original cute ghost in a Loy Krathong outfit, less painted imagery across the site and contextual UI interactions. This supersedes the illustrated hero/card direction from PR 35.

The exercise tile reuses `static/images/jeff/page-31.jpg`. Other activity tiles use existing small UI icons and native controls rather than large generated paintings. The original ghost outline, eyes, smile and cheeks from `power-garden.svg` are reused as editable inline SVG; sabai, flower, arm, krathong and flame are separate UI elements. CSS independently animates bobbing, blinking, waving, candle flicker and floating krathong. Click, Enter or Space gives a greeting and bounded feedback.

Contextual particles follow category metadata: health hearts, workout strength, calendar, cardio lightning, trophy, gift, chat, friends and boxing symbols. Ordinary clicks retain the golden lightning fallback. The effects preference, size setting and reduced-motion option remain effective. The ghost pauses offscreen/off-page; bursts are capped, cleaned up and never enter the boxing controls or arena. Core match logic is unchanged.

## Findings and fixes

1. Homepage: the user's supplied references show a painted banner replacing the former playful mascot. Restored a centered mascot UI and the original human photo. Native text and buttons remain accessible.
2. Activity navigation: contextual feedback now reinforces the clicked category. Health hearts and five other categories were exercised in a real browser. Original handlers, forms and destinations remain intact.
3. Small mobile header: at 320 px, the settings button overlapped the second theme button. The theme row now gets separate vertical space; browser hit-target assertions verify access to the right edge of the button.
4. Fight Club: the supplied lobby screenshot showed a painted gym banner stacked over a separately rendered 3D gym. Removed the painted banner. The header now overlays one continuous live 3D scene. Saved avatar/LV, growth values, shared controls, practice, two-player movement and combat passed the existing local browser suite.

The user's additional unspecified bug report was queried; no concrete gameplay symptom was provided at review time. The confirmed visual scene mismatch and narrow-header overlap are the bugs fixed here. These checks do not establish universal device performance or cover an unknown symptom.

## Validation

Passed on a disposable local database at port 5083:

- `tests/qa_festival.py`: 1440/768/390/320 px, both themes, original photo, single image card, native ghost, keyboard greeting, contextual health feedback, reduced motion, English navigation, existing grounded-step invariants and no JS errors.
- `tests/qa_motion_ui.py`: actual transform change between frames; six category effects; Space action; rapid-click bounds; persisted effects-off; reduced-motion behavior; no JS errors.
- `tests/qa_boxing_lobby.py`: saved characters/LV, mobile/desktop lobby, settings/remaps, practice, two-client match movement/stop, kicks, guard, dash, camera lock, navigation recovery and cleanup.
- `tests/verify_live_boxing.py local http://127.0.0.1:5083`: read-only release smoke, including new homepage interactions and existing public 3D fixtures.
- `tests/test_installer.py`: 2 tests passed. JavaScript syntax and `git diff --check` passed.

Editable native-vector design: https://www.figma.com/design/dNjMN9y08c1nLEDh601lxU . The website is the runnable animation reference; Figma retains editable layout/vector layers.

Figma limitation: the Starter-plan MCP quota was exhausted on the final portrait crop adjustment. The native ghost, lotus, editable text, revised cards and restored photo are present; the Figma photo still uses the default center crop rather than the website's verified 35% focal position. This does not affect the running website. No upgrade or additional subscription was requested.
