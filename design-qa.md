# Native Loy Krathong motion UI — design QA

Final result: **passed**

Target: the user's supplied original ghost hero and original human-photo exercise card, with Loy Krathong styling and native motion. The earlier generated-painting concept is superseded by this explicit correction.

| Check | Result |
| --- | --- |
| Layout and typography | Restored centered 45 FITNESS COACH title, Thai/English supporting text, responsive native controls. Verified at 320, 390, 768 and 1440 px. |
| Character identity | Reused the original SVG ghost outline and face; editable sabai, flower, waving arm, separate krathong and candle. No raster hero background. |
| Photograph | Original `jeff/page-31.jpg` restored with the original 35% focal position. Only this activity card retains a photograph. |
| Color | Purple/mint/gold night scene and readable light-theme variant. Native text colors checked in the browser. |
| Motion | Actual computed transform changes; independent float/blink/wave/flicker; offscreen pause; keyboard interaction; reduced motion and stored effects preference. |
| Category feedback | Health hearts and five other category symbols verified. Global bursts capped at 20, ghost wish capped at one; boxing controls remain free of particles. |
| Bugs | Removed competing painted/3D lobby scenes; fixed 320 px theme/settings overlap; checked theme control hit targets. |
| Regression | Two-client boxing, saved appearance/LV, input settings, navigation and public 3D release smoke passed. No backend or account data changes. |

Evidence: [desktop](docs/motion-ui/home-desktop.png), [mobile light theme](docs/motion-ui/home-mobile.png), [320 px](docs/motion-ui/home-small-mobile.png), [health feedback](docs/motion-ui/health-feedback.png), [lobby desktop](docs/motion-ui/lobby-desktop.png), [lobby mobile](docs/motion-ui/lobby-mobile.png).

[Detailed findings, validation and limits](docs/motion-ui/README.md) · [Editable Figma](https://www.figma.com/design/dNjMN9y08c1nLEDh601lxU)
