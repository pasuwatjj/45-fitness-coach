# V44 validation — 30 October 2026

## Executed

- Python compile checks for supplied/new `.py` files.
- Node syntax checks for new renderer, editor and profile-energy scripts.
- 21 focused Python unit tests with a temporary SQLite store and minimal mocked base-module interfaces: old character settings, facial-setting round trips, owner rejection, invalid inputs, silhouette updates, dimensions privacy, energy formula, retry idempotency, pause, static pose/camera translation, tracking gaps, occlusion, local-midnight split, profile separation, missing weight, weight snapshots, resistance/cardio categories, profile deletion, invalid dates, missing-base installer rejection and preserving unrecognized local edits.
- 27 Three.js geometry combinations (3 fullness × 3 eye × 3 nose settings): finite vertices and normals, plausible model bounds, articulated transforms and disposal. These use actual Three.js geometry/math with no WebGL context; they are not browser rendering tests.
- Software projection of the generated mesh was inspected for silhouette and overlapping parts; this is a geometry diagnostic, not a browser screenshot. Contours, hair and shorts were refined after inspection.

## Not verified

- Full Flask boot: base dependencies such as `leaderboard.py`, `sessions.py`, `accounts.py`, `exercises.py`, original `static/profile.js` and other base files are not contained in V42/V43.
- Full account/save/profile integration against the team's production database.
- Actual WebGL output, mobile Safari/Chrome appearance and frame rate. Managed preview started, but the browser tool failed to respond. No browser pass is claimed.
- Real camera retargeting, cardio round lifecycle on the missing base implementation, energy estimation against a wearable or metabolic measurement.
- GitHub upload/deployment. A source ZIP is supplied; no repository link or push was requested/available.

## Team acceptance checklist

1. Apply to a separate V42/V43 checkout; keep a database backup.
2. Sign in, open an old avatar, change each facial option, save and reopen.
3. Change weight/height, confirm fullness updates; verify different profiles remain separate.
4. Open camera, run curl, a leg exercise, full/upper cardio and pushup; test avatar size controls and floor pose.
5. Pause twice and refresh daily energy; totals must remain unchanged without new movement.
6. Check idle/occluded camera periods do not accumulate tracked seconds; compare 1 minute of visible movement with the displayed time.
7. Confirm two-player mode does not save energy, logout/login does not reveal another user's data, and reset analytics clears the energy card.
8. Check narrow mobile viewport, long names, dark/light themes, fallback when WebGL is unavailable and reduced-motion preference.

## Run focused checks

```bash
python -m unittest discover -s tests -v
node tests/test_geometry.cjs
```

The original V42 report in `docs/history` is historical evidence only; its old test counts have not been rerun here.
