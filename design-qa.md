# Loy Krathong fitness and Fight Club — design QA

Final result: **passed**

Selected direction: midnight river, gold candlelight, cute athletic characters.
The user delegated visual selection and approved implementation in the existing app.
Source: [selected concept](docs/loy-krathong/selected-concept.png).
Rendered comparison: [same 1487 × 1058 viewport](docs/loy-krathong/reference-viewport.png).
The implementation adapts the concept to the existing account/navigation and preserves all destinations.

| Area | Evidence and final result |
| --- | --- |
| Typography | Thai/English headings, readable Thai line height, 62 px maximum desktop title and 32 px mobile title. No truncated control labels at 390, 768, 1440 px. |
| Layout | Split desktop hero, stacked mobile illustration, three featured modes followed by existing destinations. Desktop header overlap fixed by reserving header height; transparent language-row hit area no longer blocks theme controls. |
| Color | Midnight/teal/gold plus cream/forest alternate theme. Fixed inherited light-theme text colors over dark art; browser asserts exact readable gold/cream values in both themes. |
| Imagery | New optimized WebP hero, strength/cardio/boxing cards and gym header. Existing brand logo and approved Quaternius fighter remain in the app. Decorative images have empty alt attributes; navigation retains text. |
| Copy | Clear primary training and calendar actions; existing profile, VIP, friends, rewards, history and exercise destinations preserved. Thai and English checked. |
| Motion | Gold lightning replaces click bats in both themes, follows existing toggle and size settings, and is disabled with reduced motion. Gameplay and menus do not spawn click particles. |
| Boxing | Teal/gold gym header, separate training/friends/bot cards, readable growth panel, arena frame/control treatment. Desktop/mobile lobby screenshots inspected. |
| Movement | Supporting foot stays in world space during a computer-controlled stance. Speed-filtered gait removes sudden step-phase changes. Actual bone drift under 0.025 world units at 30 and 60 update steps/sec; measured below 1e-14. This is a trajectory test, not an FPS guarantee. Tracking, kicks, dash and presentations retain their existing choreography. |

Evidence: [desktop](docs/loy-krathong/home-desktop.png), [mobile light theme](docs/loy-krathong/home-mobile.png), [lobby desktop](docs/loy-krathong/lobby-desktop.png), [lobby mobile](docs/loy-krathong/lobby-mobile.png), [arena](docs/loy-krathong/arena.png).

Editable design: https://www.figma.com/design/dNjMN9y08c1nLEDh601lxU
Native text, auto-layout frames and individual image fills; not a flattened screenshot.
Direct localhost capture script was unavailable because the environment denied the Figma capture host (HTTP 403). Native Figma API composition and rendered screenshots provided the review path. The Figma lobby is a visual layout reference; the website retains its live 3D preview.

Validated with local disposable accounts/database: seasonal navigation, both themes, tablet/mobile overflow, reduced motion, English copy, no uncaught JS errors; two-client keyboard combat and room mode inheritance; kicks, directional guard, dash, camera lock and navigation recovery; final-hit contact framing and desktop/mobile body visibility. No real-user data or production matches were modified by QA.
