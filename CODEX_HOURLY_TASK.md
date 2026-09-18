# ChatGPT cloud hourly migration runbook

## Current status

This repository contains the candidate implementation, not an active schedule.
Merging code does not activate ChatGPT Scheduled or disable Claude. Cut over
only after a manual end-to-end run succeeds in the same ChatGPT cloud runtime.
Then make disabling Claude and enabling one replacement a coordinated cutover;
observe a scheduled run before declaring the migration complete. Inspect
schedules first and never leave two hourly routines enabled.

The established documentation says the job runs once an hour near minute 59,
but the old scheduler timezone/phase has not been verified. Preserve it only
when the old scheduler proves it. Otherwise, use once an hour near minute 59 in
`Asia/Kolkata` as a newly selected default and report that distinction.

The connected Supabase tool owns database authentication. Vercel and Codex
environment variables are not inherited by ChatGPT Scheduled. Never retrieve,
print, prompt for, or persist a service-role key. The scheduled ChatGPT session
does the language work; there is no external LLM API dependency.

## One-time activation gate

1. List accessible Supabase projects using tools actually callable in this
   chat. Identify UAV by this schema before reading application data:
   `applications`, `scraped_jobs`, `resume_profiles`, `job_messages`,
   `cover_letter_drafts`, `message_requests`, `follow_up_history`, `email_logs`,
   `notifications`, and `push_subscriptions`. Do not restore or select a project
   based only on its name.
2. Check out the candidate PR commit in cloud compute, install
   `backend/requirements.txt`, run all Python/frontend/PostgreSQL checks, then
   repeat from the resulting `main` commit before activation.
3. Confirm public scraper sources are reachable in this exact runtime and the
   future scheduled task exposes the same GitHub and Supabase connections.
4. Execute one bounded workflow below. Verify inserted jobs, screening states,
   outreach drafts, queued request results, cover-letter drafts, and the final
   in-app notification by ID and provenance.
5. The live cover-letter gate requires either a real job whose explicit
   mandatory eligibility is `passed` and resume–JD score meets the configured
   threshold (default 90), or an honest report that no live job qualified. Use
   isolated test fixtures for threshold boundaries; never alter a real score.
   For a qualifying live job, verify the saved letter is visible on its tracker
   detail page and copy/download work; verify below-threshold, failed, and review
   jobs have no current letter. Record IDs/timestamps, not resume contents.
6. Inspect schedules again. Only after the manual run succeeds, disable the old
   Claude routine and verify its disabled state as the first half of a
   coordinated cutover; then create exactly one hourly ChatGPT task. Observe one
   real run and verify its timestamps, writes, plugin access, and next run. If
   this chat cannot inspect and disable Claude, stop before enabling the
   competitor and report the exact user action required. Never claim Claude is
   disabled without evidence.

The Supabase connector can preserve in-app notifications. It cannot sign Web
Push without a separately supported and tested VAPID signing capability, so
report push as unavailable rather than silently dropping or claiming it.

## Cloud checks

```bash
python -m pip install --disable-pip-version-check -r backend/requirements.txt
python -m unittest discover -s backend/tests -p 'test_*.py' -v
npm ci --prefix frontend
npm run build --prefix frontend
```

Exercise generated SQL against ephemeral PostgreSQL in cloud compute:

```bash
connector_test_dir=$(mktemp -d)
npm install --prefix "$connector_test_dir" @electric-sql/pglite
node backend/tests/postgres_integration.mjs \
  "$connector_test_dir/node_modules/@electric-sql/pglite/dist/index.js" python
```

## Per-run file boundary

Generate one stable run ID and reuse it in every file and notification. Export
bounded database context through Supabase; never put credentials in these files.

`scrape-context.json` contains schema version 1, the run ID, the single reviewed
`resume_profiles` row whose status is `active`, the newest email subject, and up
to 20,000 recent `existing_jobs` rows with `url`, `jd_hash`, and `jd_version`.
Paginate until a short page; stop if truncated. Legacy `existing_job_urls` may
also be supplied, but fingerprints are required to detect a changed JD.

```bash
cd backend/modules
python cloud_connector.py scrape ../../scrape-context.json ../../scrape-plan.json
python cloud_connector.py sql ../../scrape-plan.json ../../scrape-mutations.sql
```

Apply the complete transaction through Supabase and read it back. A repeated
URL+JD is ignored; a changed JD increments its version, marks analysis/drafts
outdated, and is reprocessed. Values are base64 JSON, never model-written SQL.

Then export `task-context.json` with:

- the same active PDF profile snapshot and run ID;
- `rescore_jobs` (100), the next bounded batch with `analysis_stale=true`,
  including each exact JD, hash and version. Each cycle updates only rows whose
  hash/version still match, so a new profile drains stale scores safely over
  repeated hourly runs;
- `screen_jobs` (100), filtered `dismissed=0 AND applied=0`, with no current
  screen for the active profile version;
- `outreach_jobs` (10) missing a current `cold_dm` for that profile version;
- `cover_letter_jobs` (20), filtered `dismissed=0 AND applied=0`, current
  non-stale analysis/profile version and a current `pass` screen decision,
  plus exact JD/hash/version and analysis. Export both the stored score and the
  score inside `analysis_details`; the adapter rejects any mismatch;
- `cover_letter_threshold` (default 90);
- pending requests (20), due applications (100), complete follow-up history
  (500), and active follow-up requests (200);
- completeness flags set true only after full pagination. Truncation stops the
  run because it can change follow-up numbering.

```bash
python cloud_connector.py prepare ../../task-context.json ../../task-items.json
python cloud_connector.py sql ../../task-items.json ../../followup-mutations.sql
```

Apply the rescores and follow-up inserts, then re-export the complete task
context (including newly current analyses, screen decisions, and pending
requests) and prepare again.
Compose screen decisions (`pass`, `fail`, or `review`), cold DMs, queued
responses, and every emitted `cover_letters` prompt in the ChatGPT session.
Unknown mandatory eligibility must be `review`, not pass. Cover letters are
emitted only for explicit eligibility `passed` and score at or above threshold.
Ground them only in the exact JD and active reviewed PDF facts; never invent or
inflate anything, promise ATS acceptance, send, email, submit, or apply.

Write `actions.json` with the unchanged run ID, bounded `screens`,
`outreach_drafts`, `request_results`, `cover_letter_drafts`, and one accurate
final in-app notification. Then validate, render, apply, and read back:

```bash
python cloud_connector.py validate-actions ../../task-items.json ../../actions.json ../../validated-actions.json
python cloud_connector.py sql ../../validated-actions.json ../../action-mutations.sql
```

Retries are idempotent. Cover letters are keyed by job, resume version, JD hash,
and generation-rules version; a changed resume or JD marks older drafts
outdated. Saved rows also carry match/analysis versions, run ID, generator, and
timestamp. Outreach and cover letters remain drafts in the app.

## Durable recurring prompt

```text
Run one UAV cycle entirely in ChatGPT cloud compute from current main of
https://github.com/ashishgautam0/UAV using only the connected GitHub and
Supabase tools actually exposed in this run. Do not use a desktop checkout,
manage schedules, request credentials, call an external LLM API, send outreach,
or submit applications. Generate one stable run ID and follow the per-run
boundary, bounds, stop conditions, matching/profile invariants, cover-letter
threshold, SQL validation, and read-back checks in CODEX_HOURLY_TASK.md.

Identify UAV by schema before data access. Install backend/requirements.txt in
the fresh checkout. Use one active reviewed PDF profile snapshot throughout.
Preserve scraping, filtering, deduplication, persistence, message queues, draft-
only outreach, and the final in-app summary. Flag unknown mandatory eligibility
for review. Compose only emitted requests and eligible cover-letter drafts;
ground every claim in supplied evidence. Report counts, source failures,
screen pass/fail/review, scores and threshold decisions, saved draft IDs and
provenance, queue outcomes, notification read-back, and push availability. Stop
before later writes on any schema, connection, checkout, network, truncation,
validation, SQL, or read-back failure.
```
