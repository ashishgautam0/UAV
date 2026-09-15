# ChatGPT/Codex hourly cloud task

This runbook migrates the existing `59 * * * *` Claude routine without adding
an LLM API dependency. The scheduled ChatGPT session writes drafts itself.

## Cloud environment

Create or select a Codex cloud environment for `ashishgautam0/UAV`, default
branch `main`, using Python 3.11 or newer.

Setup command:

```bash
python -m pip install --disable-pip-version-check -r backend/requirements.txt
```

Configure these under **Codex cloud -> Settings -> Environments -> UAV ->
Environment variables**:

- `SUPABASE_URL` (required)
- `SUPABASE_KEY` (required service-role key)
- `VAPID_PRIVATE_KEY` (optional)
- `VAPID_CLAIM_EMAIL` (optional)

Do not put values in this file, the repository, logs, or the task prompt. Allow
outbound HTTPS to the configured Supabase host and the public job sources used
by `backend/modules/scraper.py`.

## Saved task prompt

Save the following prompt in a cloud scheduled task. Keep the schedule disabled
until a manual cloud run succeeds.

```text
Run the UAV job-search workflow entirely in the cloud against
https://github.com/ashishgautam0/UAV on branch main. Use a fresh cloud checkout
for this run and install backend/requirements.txt. Never use or depend on a
user desktop checkout.

Before starting, do not overlap another active run of this same scheduled task;
if the platform reports one, skip this run and report that fact. Confirm
SUPABASE_URL and SUPABASE_KEY are present without printing their values. Treat
VAPID_PRIVATE_KEY and VAPID_CLAIM_EMAIL as optional and never print any
credential. If either required variable is absent, make no database changes and
report the missing variable plus the secure cloud-environment settings path.

Read README.md, CODEX_HOURLY_TASK.md, the files under .claude/agents,
backend/modules/hourly.py, backend/modules/pending_messages.py, and
backend/requirements.txt. The .claude/agents files are legacy-named but contain
the current writing and screening policy; follow them without requiring Claude.

From the repository root, run:
python -m pip install --disable-pip-version-check -r backend/requirements.txt
cd backend/modules
python hourly.py

Then run `python pending_messages.py screen-list --limit 100`. For every job,
apply the current resume-screener rules and record pass or fail with
`python pending_messages.py screen`. Do not weaken or replace the Python
filters, URL deduplication, Supabase persistence, or screening rules.

Run `python pending_messages.py followups`, then
`python pending_messages.py list --limit 10`. For each returned job, compose a
grounded cold outreach draft yourself using the stored profile and the current
cold-DM instructions. Save it through stdin with
`python pending_messages.py save --job-id <ID>`. Drafts are for storage only:
never send outreach, email, LinkedIn messages, or job applications to any third
party.

Run `python pending_messages.py requests`. For each pending item, follow its
ready-made prompt and character limit, compose the response yourself, and save
it with `python pending_messages.py fulfil --request-id <ID>` through stdin. If
an item contains an error or cannot be grounded, use
`python pending_messages.py fail --request-id <ID> --error <reason>` instead of
inventing facts. Do not call an external LLM API and do not require an LLM API
key.

Finally run `python pending_messages.py notify --title "Job scan" --body
"<accurate summary>"`. This must create the existing in-app summary; optional
web push may be skipped when VAPID settings are absent. Report counts for jobs
found, saved, screened pass/fail, drafts saved, requests fulfilled/failed,
notification status, scraper errors, and whether optional push ran. Do not
include secrets or full profile text in the report.
```

## Activation sequence

1. Run the saved prompt manually in the configured Codex cloud environment.
2. Verify dependency installation, source reachability, Supabase reads/writes,
   queue processing, stored drafts, and the in-app notification.
3. Enable one task with `DTSTART` at minute 59 and
   `RRULE:FREQ=HOURLY;INTERVAL=1` in the user's timezone.
4. Confirm the task appears once in Scheduled and inspect its first run.
5. Disable the old Claude routine only after steps 1-4 succeed.

Never run both schedules beyond the brief validated cutover.
