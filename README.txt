45 Fitness Coach v29 — 24 October 2026
Complete release: includes v26 + v28 repairs + whole-app cute themes.
อ่าน DEPLOY_V29_TH.txt และ FEATURE_AUDIT_V29.txt ก่อนอัปโหลดทั้งชุด
ไม่ต้องติดตั้ง v27/v28 ก่อน — ผลทดสอบ TEST_REPORT_V29.txt — ยังไม่ได้ Deploy

Historical notes follow; v29 guide takes precedence.

45 Fitness Coach v28 — 24 October 2026
อ่าน DEPLOY_V28_TH.txt สำหรับการอัปโหลดทั้งชุดจาก v26 และการเปลี่ยนหน้าจอ/เสียงล่าสุด
ผลการทดสอบ: TEST_REPORT_V28.txt — ยังไม่ได้ Deploy

45 Fitness Coach v22 — see V22_README_TH.txt.
45 Fitness Coach v21 — see V21_README_TH.txt for new features and permanent domain setup.
45 FITNESS COACH v20
Read V20_README_TH.txt and TEST_REPORT_V20.txt first.

45 FITNESS COACH v19
Read V19_README_TH.txt for the current update.

45 FITNESS COACH v18
Read V18_README_TH.txt for installation and features; TEST_REPORT_V18.txt for verification limits.

45 FITNESS COACH v16
Read V16_README_TH.txt first. Latest camera, VIP/admin, friends and tutorial update.

Historical instructions below:
45 FITNESS COACH v14

Open the home page and train as a guest. Create an account from the account icon
for cross-device history and VIP. Guest data belongs to the browser cookie;
signup in that browser adopts its history. A stored profile is selected again.
Recovery numbers are hashed, 8-12 digits, with persistent rate limits and a
5-minute one-use reset ticket. Existing accounts must sign in and set a number.
Reset revokes all account logins; no recovery secrets enter the client response.

Jeff's supplied PDF pages replace 13 exercise guides; all steps are retained.
The 2 exercises without supplied images retain their previous illustrations.
Page 31 is the home portrait. The Bench Press images show a floor variation;
the guide labels this distinction. The introductory panel is hidden.

Camera status cannot close or rewind a newer active stream. Control replies
adopt fresh state; stale in-flight frames are dropped and pumping continues.
Brief mobile app/permission interruptions no longer trigger the old 2.5s stop.
Fullscreen and normal camera views show accepted reps in the upper-right corner.
Curl keeps the 80-degree default, now with 10-degree count allowance. Small arm
drift is advice; clear body-relative sideways/backward motion rejects the rep.
Red split coin and glass sound remain. Pose estimates are not certified form.

VIP Home: 50 THB / 30 days. QR/account are visible. Sign in before paying.
With configured SlipOK and SMTP, verified payments activate VIP automatically.
Otherwise receipts are stored for manual bank-transfer review; upload alone
does NOT grant VIP. A local operator can confirm actual payment with manage_shop.py.
SMTP must be configured for receipts to reach 67011241@kmitl.ac.th; otherwise
they remain queued. Setup-VIP.ps1 supports email-only/manual mode (blank Branch).
Keep Start-Configured.ps1 running for the durable email worker.

The rewards preview and whey picture are visible to everyone. Only VIP can
convert 10 gold to 1 purple or request whey for 50 purple. The operator confirms
variant, stock and delivery. Pending cancellation refunds once. Third exercises
remain VIP-locked server-side including calendar starts, resets and resumes.

UPDATE: use UPDATE_POWERSHELL.txt. Read V14_README_TH.txt and VIP_SETUP_TH.txt.
No actual bank payment, SMTP delivery or physical mobile camera test was made
in this environment. Automated tests use simulated camera/payment outcomes.
Database, accounts, photos and service secrets in data/ are not in either ZIP.

HISTORICAL RELEASE NOTES (v14 behavior above takes precedence)


V12 CHANGES (supersede the older reward description below)
Camera polling pauses during control/startup operations. Stale status errors do
not close a newer stream. Stop requests carry their set ID, so delayed stops from
older sets are ignored. Camera acquisition retries transient hardware-busy errors
once. Start responses include the new state. Existing frame-failure limits remain.
Curl/Hammer upper-arm direction checks are stricter, with a short jitter filter.
Rejected attempts show a red coin splitting into two pieces and a glass-like
synthesized sound; a Test broken-coin sound button enables an audible preview.
These remain experimental geometry rules, not complete form or safety validation.

Challenges: join Biceps Curl x20 before opening the camera. Only accepted new reps
count; both-arm mode requires completed pairs. Progress accumulates across saved
sets. Reaching the remaining target automatically pauses/saves and awards exactly
ONE purple coin. Starting again creates a new challenge. Old history, wrong reps,
other exercises and repeated save requests cannot mint additional purple coins.
Pause/Stop saves partial progress. Each profile has its own balance.

Rewards shop: shows purple challenge coins and completed training-day fire.
Whey, creatine and other gym items are labelled Coming soon, with no prices,
orders, shipping or currency deductions. Legacy badge/coin records are preserved;
legacy redemption POST actions are disabled. Rep coin animations are not purple
redemption currency. No VIP/payment/slip/email system is included in v12.

Verification: 119 Python tests passed, including all 15 exercise start/stop cycles
with mocked detectors, old-stop rejection, challenge deduplication and ownership.
The simulated bilingual UI passed repeated camera-open/status-failure checks.
Physical iOS/Android cameras and a live Windows tunnel still require device tests.

OLDER RELEASE NOTES

NEW IN V10
Top-right My Profile links to existing player names and can create another owned
profile. The selected name is shared with workout and health controls.
Avatar uploads accept JPEG/PNG/WebP up to 3 MB and 16 megapixels, normalize to a
384-pixel centre-cropped JPEG, remove source metadata, and store privately in
SQLite. Avatar and dashboard APIs require the same authenticated owner/session.
The dashboard shows all-time saved-set totals, current/best/total completed
training days, latest health inputs, up to 30 health measurements, and up to 60
recent saved sets. Exercise-filtered charts show up to 20 recent sets. The donut
uses reps with/without recorded advice, NOT a correctness or medical score.
Per-set advice events may overlap and do not equal the number of flagged reps.
Unseen/uncertain form is not certified by a green segment. No sample scores are
inserted. Empty profiles show an empty state until data is saved.
Back to home and clickable brand headings return to the category overview.
The tolerance label is now 'เผื่อองศาการนับที่ง่ายขึ้น'; thresholds are unchanged.

V11 FORM GATE AND DIGITAL REWARDS
- Exercise-family rules inspect the visible 3-D body axis, upper arm and forearm
  direction in addition to joint excursion. Curl/Hammer: upper arms stay beside
  the torso while forearms move forward. Rows, presses and raises have different
  motion-plane checks; leg exercises retain hip/knee and torso checks.
- A sustained detected mismatch marks the completed attempt red, synthesizes a
  short glass-shatter effect and does NOT increase reps, plan credits or coins.
  Speed alone and optional range advice do not reject an otherwise accepted rep.
- Direction cannot be established: neutral grey 'Unclear', no rep awarded. Show
  both shoulders, hips and the working arm. Brief jitter is filtered. This is an
  experimental geometry gate, not complete form/grip/spine validation. It cannot
  verify load, support contact, secure fingers or every camera angle.
- Coin effects are larger, follow the elbow and respect sound/motion preferences.
  No new detector/model has been added; preview and one-in-flight analysis remain.
- Home > Redeem rewards: 1 accepted rep in a NEW saved v11 set = 1 coin. Both-arm
  mode awards 1 per completed pair. Save via Pause/Stop. Old reps are not converted.
  Each completed scheduled day can claim 10 bonus coins once, including previous
  completed days. Claiming never reduces the streak or ranking.
- Redeem coins for private digital profile badges (30/80/150 coins). No physical
  goods, cash or shipping. Balances/unlocks are private per profile and persistent;
  repeated requests do not award/spend again. Clients cannot supply coin amounts.
- v11 profile rings/bars show accepted, rejected and unclear arm attempts, whereas
  the number next to the bar remains counted reps (completed pairs in both mode).
  Older sets retain their original advice graphs. A passed gate is not a safety
  certification or a measured form-accuracy percentage.
- Quick check on your devices: enable coin sound; use Curl with upper body visible;
  complete one controlled curl then one sideways example without heavy weight.
  Verify gold +1 vs red no-count, then Pause and inspect profile/rewards. If tracking
  is uncertain, adjust the view and lighting rather than forcing joint positions.

V9 FEATURES RETAINED
After login, a branded overview opens first: exercise categories, calendar,
discipline ranking and health. Thai/English is selectable from login/home;
the language URL overrides localStorage and the translation file bypasses cache.
Windows text loading explicitly uses UTF-8. No manual encoding repair is needed.
Camera startup ignores stale status requests; temporary visibility interruptions
have a grace period (2.5 seconds, 15 seconds during permission/startup). Page exit
still stops immediately. Persistent frame failures retry with backoff before stop.
Fast complete sampled motion can count without endpoint dwell; tempo is advice.
If frames miss an entire movement, a rep cannot be reliably reconstructed.
Curl/Hammer hand landmarks show yellow finger lines (21 points per detected hand).
This is tracking, not proof of a secure grip or finger-by-finger form correctness.
Start enables audio when tutorial/coin options are enabled, unless explicitly
muted with the sound button. Online audio still depends on browser/provider access.
Replay instructions is a direct-gesture button for mobile playback restrictions.
Coin effects rise near the observed elbow; with stale/unclear pose they use the
camera center. Effects respect reduced-motion preferences and clean up afterwards.

V8 FEATURES RETAINED
Curl/Hammer Curl use upper-body view, torso/upper-arm movement, visible shoulder
level and experimental hand/wrist checks. Curl counting target starts at 80
degrees with 5 degrees allowance, adjustable 40–100. This is a counting setting,
not a universal anatomical target. Optional range advice does not invalidate reps.
Palm-plane checks are experimental: they cannot reliably distinguish all grips,
pronation/supination or confirm a dumbbell. Obscured hands are marked unverified;
movement reps can still count. A stable observed grip mismatch rejects the completed attempt (red coin); uncertain grip is not certified.
Each of 15 exercises has illustrated start/end guides and optional spoken intro.
Thai/English changes interface and coaching speech; switching stops/saves/reloads.
Fire ranking uses completed planned days, skips rest days and breaks on missed days.
Local camera preview requests up to 30 fps separately from slower server analysis;
only one compressed frame is in flight. Actual speed depends on device/network/PC.
Refresh saves/stops first. Large camera view uses fullscreen where supported,
otherwise an in-page expanded view. A configurable rest timer never auto-starts.
Existing accounts and data remain. These are training aids, not medical assessment.

SETUP / UPDATE
Windows PowerShell instructions: UPDATE_POWERSHELL.txt and QUICK_START_TH.txt.
Use the existing Python3.11 environment. Full ZIP includes the pretrained model;
Update ZIP preserves the existing model, database and environment.
Stop both PowerShell windows and close all old website tabs before updating.
Start app.py; open localhost on the computer and register the owner's account
FIRST. Pre-v7 unowned profiles are adopted by that first local account.
New remote accounts cannot adopt legacy names by guessing them.
Then run Start-Share.ps1 in the second PowerShell window for the HTTPS URL.

ACCOUNT MODEL
Email/password registration and login precede workout UI. Passwords use scrypt;
revocable login cookies are HttpOnly/SameSite Strict and Secure on the HTTPS tunnel.
Accounts, hashed login tokens and workouts persist in data/fitness.db.
Each account can have several nicknames; nicknames are unique across this server.
Accounts can log in from multiple devices or after the share hostname changes.
Each page gets a separate unpredictable token, bound to its login cookie.
Private profile/health/calendar APIs require ownership. Shared ranks expose only
nicknames and saved activity scores. The access link alone does not grant account
access. Email is an identifier, not proof of ownership: email verification,
password reset delivery and Google sign-in are not implemented.
The first local account owns all legacy data; migrate before inviting others.

CAMERA MODEL
getUserMedia captures EACH browser's own camera with audio:false. Frame JPEGs
(max640 pixels on longest side) go to a dedicated server PoseLandmarker/counter
for that tab; landmark JSON returns on its authenticated frame request while
the local video remains independent. Legacy clients can request annotated JPEGs.
No host camera is opened by web APIs. No public MJPEG feed remains.
The computer is still required for inference and SQLite. Frames traverse the
HTTPS tunnel/Cloudflare; videos are not recorded to disk.
Phones must use HTTPS in Safari/Chrome. HTTP LAN URLs cannot request phone cameras.
The localhost computer URL is permitted by browsers. Switch apps/lock screen:
camera tracks stop after a short grace period and that page's session saves. Lost frames for over20 seconds
stop/save on the next5-second cleanup pass; gaps over2 seconds recalibrate.
One in-flight frame per tab, about12fps maximum, adapts to network latency.
At most8 camera sessions are admitted; hardware may handle fewer smoothly.
Each profile has one active workout writer, avoiding cross-tab plan collisions.
Different accounts/profiles can exercise concurrently. Scoreboard alone is shared.

VOICE MODEL
Only the selected provider speaks. The default is explicitly Neural female.
There is NO automatic fallback to device/Siri or gTTS on a provider error.
All speech starts pass a generation guard; changes cancel audio and speechSynthesis.
Changing speed stops current speech; the next phrase uses the new speed.
Same-browser tabs coordinate sound ownership through BroadcastChannel.
A phone/browser may require tapping Test Voice to permit audio.
Online providers receive only fixed public phrases, not images or health records.
OpenAI needs a server-side API key and separately billed API usage.

BOTH ARMS
Each arm calibrates, smooths and counts independently. Overall pairs equal
min(left completed reps, right completed reps). One rep on each side is one
pair, whether synchronized or alternating. Missing one arm cancels that arm's
unfinished movement; the other can continue. Keep both arms unoccluded.

CAMERA / FORM LIMITS
Single arm: side/diagonal view. Both arms: front/slight diagonal without overlap.
Estimated3D model landmarks are preferred for elbow angle, with pixel-scaled
2D fallback; neither is an exact anatomical measurement. Arms focus compares
upper-arm direction with image vertical and does not grade torso. Upper focus
requires hips and adds torso checks. Wrist alignment, palm rotation, spinal
shape and shoulder shrug aren't graded. Good lighting and an upright fixed
camera matter. A count or no warning doesn't certify complete correct form.
The previous Exercise2 placeholder is replaced by the 15-exercise catalogue.
Leg movements require shoulder/hip/knee/ankle visibility. Presses and rows
require torso visibility; curls can still use the closer arms-only framing.
New movements use family-specific joint-angle heuristics, not a trained
exercise classifier. Palm grip, bench angle and actual dumbbells are not
automatically verified. Chest/lying movements can lose landmarks behind
benches or limbs; use the stated view and do not rely on counts as form proof.

TECHNIQUE REFERENCE / SETTINGS
Mayo Clinic supports controlled curls, elbows near the body, avoiding swing,
and straight wrists. It does not specify the numeric cutoffs used here:
https://www.mayoclinic.org/healthy-lifestyle/fitness/multimedia/biceps-curl/vid-20084675
Angles, dwell times, noise margins and tempo cutoffs in settings.json are
engineering choices requiring real-camera/user testing. Shorter accepted
movement paths scale tempo detection to reduce misleading speed warnings.
Stop if painful rather than forcing movement to match a number.

CALENDAR RULES
Weekly upload maps Monday=0 through Sunday=6 from the chosen start date to the
end of that month. It does not generate an exercise prescription: set/repetition
defaults are editable examples. Empty days are explicitly rest days.
Each profile owns its dates and plan items. Play today resolves the next target
on the server, pauses at the goal and awards one unique set credit. Repeated
save requests cannot award another slot. All items/sets must be credited before
that date receives its check. Free-play scores do not retroactively complete plans.
Partial attempts remain in activity history but must be retried as a complete
set. Completed sets survive app restarts; unsaved frames/reps do not.
The calendar follows UTC+07:00 (Thailand). Training cannot backfill past dates.
Past days and days with at least one completed set cannot be rewritten by the
calendar editor. Today's active plan is also protected while the camera runs.
Streak = consecutive scheduled training days completed; rest/unplanned days are
neutral. An incomplete past scheduled training day resets the streak; today
remains possible until midnight. A paused session crossing midnight cannot
credit yesterday and must open today's plan again.
Single-arm row and split squat need separate left/right plan entries when
training both sides. Squat and RDL are bilateral movements: select the visible
side for tracking, not a one-legged exercise.


FILES
app.py: private browser coach, inference, Flask routes and sharing.
accounts.py: email/password authentication, hashed passwords and revocable cookies.
sessions.py: per-tab lifecycle and profile ownership.
static/session-camera.js: sign-in, camera capture and authenticated frame transport.
static/app.js: workout interface and single-provider audio.
static/planner.js / planner.py: calendar UI, target credits and streaks.
form_rules.py / curl_counter.py / motion_coach.py / exercises.py: motion heuristics.
leaderboard.py / health.py: profile persistence, scores and basic health arithmetic.
Start-Share.ps1: temporary public HTTPS tunnel, official Cloudflare binary.
Install-Update.ps1: backup/copy/install/start through PowerShell.

TESTS
..\.venv\Scripts\python.exe -m unittest discover -q
111 Python tests passed. JavaScript camera/session, voice-race and rest-timer checks passed in
a simulated DOM. Real MediaPipe initialized and processed a blank frame to JPEG.
Rendered-page DOM integration passed for both languages, profile charts, brand/home navigation,
camera startup, teaching playback calls, short visibility interruptions and coins.
This uses simulated media, not real mobile hardware or full browser rendering.
Synthetic motion and server tests do not establish real-world accuracy or medical
validity. Actual iOS/Android camera permissions, Thai voice provider availability,
and a live Windows Cloudflare tunnel still need testing on the user's devices.

REFERENCES
https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python
https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
https://developers.cloudflare.com/tunnel/downloads/
https://www.cdc.gov/bmi/adult-calculator/bmi-categories.html
https://www.cdc.gov/bmi/faq/index.html
https://github.com/rany2/edge-tts
https://developers.openai.com/api/docs/guides/text-to-speech
