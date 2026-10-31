# 45 Fitness Coach development workflow

Continue the existing repository and latest main; do not rebuild the site or replace
its approved Quaternius avatar. Preserve accounts, VIP status, rewards, workout
history, profile information, and unrelated features. No destructive migrations.

For a user-approved development task, implement on a dedicated branch, run relevant
unit/browser/regression tests, and fix critical failures. Create or update the PR
into main (continue an existing task PR rather than duplicating it). Once the approved
scope is finished and critical checks pass, merge automatically. The existing Render
service deploys main automatically; do not create another service or use other hosting.
Verify the deployed revision and feature on the existing live site before claiming
completion: https://four5-fitness-coach.onrender.com/45-fitness-coach
If deployment breaks the site, recover to the last known working revision where possible.

Ask before destructive changes, major architecture changes, or work outside the
requested scope. A new explicit task constraint overrides this default workflow.
Use disposable local databases for test accounts and synthetic workouts. Prefer
read-only live smoke checks. Report PR, deployment status, live URL, tests, and limits.
