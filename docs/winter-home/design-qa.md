# Winter home — Product Design QA

final result: passed

## Target and evidence

The user requested replacing the existing Loy Krathong homepage with a snowy winter theme, using native UI and smooth wind-driven snowfall. The supplied FiveM winter image-search screenshot is a mood reference (ice blue, white snow and frosted surfaces), not a layout to clone. The explicit request for UI takes precedence over preserving the reference's raster character posters. No Figma file or frame was supplied; no Figma document was created or modified.

The existing code target was captured before editing: `docs/winter-home/before-desktop.png`. Implementation evidence: `docs/winter-home/home-power-1440.png`, `home-spicy-1440.png`, `home-power-390.png`, `home-spicy-390.png`, and `home-power-320.png`.

- Source CSS viewport: 1440 × 1000, device scale factor 1; source bitmap 1440 × 1874. Thai, guest, light theme.
- Comparison implementation: 1440 × 1627 bitmap, same 1440 × 1000 CSS viewport, density, language, guest state and light theme. Full-page lengths differ intentionally because the hero and photo-led category grid were redesigned.
- Combined full-view evidence: `docs/winter-home/comparison-desktop.png` puts the actual source and implementation in the same browser-rendered comparison, at equal displayed widths.
- Combined focused evidence: `docs/winter-home/comparison-hero.png` shows the hero, CTA area and first category row together. This is an intentional seasonal redesign, not a claim of pixel fidelity to the former screen.
- Additional captures/tests cover dark/light at 390 px, tablet at 768 px, and compact 320 px. Original full-size screenshots remain available for reading small copy; the comparison board scales both columns equally.

## Findings

No actionable P0/P1/P2 findings in the first rendered comparison and interaction pass. The winter palette, separate live mascot, UI category ornaments, bounded background particles and preserved routes meet the brief. A dedicated pause control prevents ambient motion from being compulsory.

| Required surface | Review |
| --- | --- |
| Typography | Retains the app's loaded font/fallback stack. Strong title, Thai subtitle, readable body hierarchy. Title and CTA wrapping checked at 320/390/768/1440 px; no clipped text or horizontal overflow. Small scene captions are decorative; actions and feature descriptions retain separate readable labels. |
| Spacing/layout | Split hero on desktop, stacked copy/scene on mobile, 3/2/1-column category grid. The primary training action remains before the mascot on mobile. Logo, theme controls, account bar and settings stay operable. |
| Colors/tokens | Dark navy/ice blue and bright frost variants, with opaque-enough content surfaces separating text from the snow. Semantic health/cardio accents preserved. Non-home body tokens and gym-specific appearance retained. |
| Assets | Native SVG snow friend, scarf/wave/blink animation, semantic line icons and 2D canvas snow. No added bitmap/video background; the former home photo panel is now a UI card. Real instructional exercise images remain intact. Logo retained. |
| Copy/content | Seasonal label reads WINTER SEASON. Thai/English copy describes form learning, camera training and progress. The 24/7 chip describes availability, not invented sensor data or live weather. No visible Loy Krathong decoration remains. |

Comparison history: first implementation and matched-state comparison passed; there were no visual-fix iterations or unresolved design deviations. The change from a centered hero to a split hero and removal of the decorative workout-card photo are intentional responses to the UI-led brief.

## Tested interactions and performance

- `tests/qa_winter.py`: native snow pixels change over time, capped 88 desktop / 42 mobile particles, one canvas, about 59.8 fps in the local headless Chromium sample. This is not a physical-device performance guarantee.
- Snow pause/resume persists after reload. Global effects settings and reduced-motion preferences stop animation. Leaving home, document visibility changes and page lifecycle stop the RAF loop; returning resumes without a time jump. Offscreen mascot animation pauses.
- Keyboard Enter/Space activates the snow friend; rapid clicks keep at most 5 scene flakes and 20 existing click-feedback particles. Snow cannot intercept pointer input.
- Training CTA expands categories; real tutorial images remain. Calendar/health navigation and contextual heart effects work. Thai/English labels and greetings verified.
- `tests/qa_motion_ui.py`: six semantic category effects, keyboard interaction, rapid-click bounds, settings persistence and reduced-motion behavior passed.
- `tests/qa_festival.py` (retained legacy regression entry point): updated seasonal selectors, responsive themes, navigation, effects and unchanged boxing foot-plant fixture passed.
- No JavaScript console errors in these browser runs. Changed JavaScript syntax and installer tests passed; manifest includes both new seasonal files and cache versions in both templates.

## Implementation checklist

- [x] Replace festive ghost/krathong with an interactive snow studio.
- [x] Apply winter UI tokens, frosted panels and native category icons.
- [x] Add wind-driven snowfall, pause control and lifecycle cleanup.
- [x] Keep exercise, profile, game and account routes/data behavior.
- [x] Check both themes, responsive layouts, keyboard use and motion preferences.
- [x] Save browser evidence and regression results.

Follow-up polish: none required for this scope. Residual test limits: actual low-end mobile GPU and Safari performance were not benchmarked. Production verification is performed after deployment using public assets and GET-only browser smoke checks.
