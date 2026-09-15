# ChatGPT Work hourly migration runbook

## Status and invariants

This is a **proposed replacement**, not proof of an active schedule. The old
Claude routine stays enabled until one complete run succeeds in the same
ChatGPT Work runtime and exactly one replacement appears in Scheduled.

The repository documents an hourly run at minute 59, but the original
scheduler's timezone has not been verified. Inspect the old scheduler before
claiming that its phase was preserved. If its timezone cannot be recovered,
activate the replacement hourly at minute 59 in `Asia/Kolkata` as the user's
new default, clearly labelled as a new default rather than a legacy setting.

The database credential boundary is the connected Supabase plugin. Vercel and
Codex cloud environment variables do not flow into ChatGPT Work scheduled
tasks. Never request, retrieve, print, persist, or put a Supabase key in a
prompt, file, log, or repository. The scheduled session itself supplies the LLM
work; no additional LLM API is used.

`backend/modules/cloud_connector.py` accepts bounded JSON exported by connector
reads, reuses the Python filters and prompt builders, validates composed actions,
and renders mutation SQL whose values are base64-encoded JSON. Identifiers and
operations are allowlisted; generated prose never becomes SQL syntax.

## Manual validation gate

In the exact ChatGPT Work cloud chat that will own the schedule:

1. Confirm GitHub and Supabase tools are callable. List Supabase projects using
   the connector's actual exposed project-list action. Do not infer tool names.
2. Identify the UAV project by schema, not by a guessed project name. Before
   reading application data, execute this read-only query on each candidate:

   ```sql
   select table_name, column_name, data_type
   from information_schema.columns
   where table_schema = 'public'
     and table_name in (
       'applications', 'scraped_jobs', 'email_logs', 'notifications',
       'user_profile', 'job_messages', 'message_requests',
       'follow_up_history', 'push_subscriptions'
     )
   order by table_name, ordinal_position;
   ```

   Compare the result with `supabase/schema.sql`. Stop without reading task data
   if the fingerprint does not match.
3. Before merge, check out the candidate PR commit in cloud compute (not
   `main`) and run
   `python -m pip install --disable-pip-version-check -r backend/requirements.txt`.
4. Export only the bounded context described below, run the Python commands,
   apply the generated SQL through the authenticated connector, then verify the
   written rows with read-only connector queries.
5. Confirm the scraper can reach its public sources in this same runtime. The
   scheduler must use the same connected GitHub and Supabase tools.
6. After the candidate commit passes, merge the PR, check out the resulting
   `main`, and repeat the non-mutating checks plus one controlled workflow run.
7. Only after all checks pass, inspect Scheduled again, create exactly one task,
   run it once, verify the next run and its plugin access, then disable the old
   Claude routine.

Before live validation, exercise the generated SQL against an ephemeral
PostgreSQL engine in cloud compute. This test applies `supabase/schema.sql` and
checks retries, queue state transitions, Unicode/quoting, per-run notifications,
and transaction rollback:

```bash
connector_test_dir=$(mktemp -d)
npm install --prefix "$connector_test_dir" @electric-sql/pglite
node backend/tests/postgres_integration.mjs \
  "$connector_test_dir/node_modules/@electric-sql/pglite/dist/index.js" \
  python
```

## File boundary

Create `scrape-context.json` (never commit it) with schema version 1:

```json
{
  "schema_version": 1,
  "run_id": "one stable identifier generated once for this run and reused in every file",
  "existing_job_urls": ["URLs scraped during the last 14 days"],
  "user_profile": {"the single username=subidh row, or an empty object"},
  "last_email_subject": "the newest email_logs.subject, or an empty string"
}
```

Fetch the URL window in pages of at most 1000 until a short page is returned;
abort if it exceeds the module's 20,000-URL safety bound. Then run:

```bash
cd backend/modules
python cloud_connector.py scrape ../../scrape-context.json ../../scrape-plan.json
python cloud_connector.py sql ../../scrape-plan.json ../../scrape-mutations.sql
```

Apply the entire generated transaction through the Supabase connector. The job
insert is `ON CONFLICT (url) DO NOTHING`; digest and notification inserts have
duplicate guards.

Afterward export `task-context.json` with these bounded arrays:

- `screen_jobs` (100): `scraped_jobs` filtered with `dismissed=0` and
  `applied=0`, with no `job_messages` row whose `message_type='screen'`, newest
  first. These predicates intentionally match `tracker.get_scraped_jobs()`.
- `outreach_jobs` (10): `scraped_jobs` whose URL appears in a non-terminal
  `applications` row and which have no `cold_dm` message, newest first. Terminal
  statuses are `Offer`, `Rejected`, `Ghosted`, and `Not Interested`.
- `pending_requests` (20): pending `message_requests`, newest first.
- `due_applications` (100): non-terminal applications with non-null
  `follow_up_date <= current_date`, most overdue first.
- `follow_up_history` (500): history for those due application IDs.
- `active_followup_requests` (200): pending or ready follow-up requests.
- `user_profile`: the same single profile row.
- `run_id`: exactly the same stable value used in `scrape-context.json`.
- `completeness`: set `follow_up_history` and `active_followup_requests` to
  `true` only after complete pagination. If either result was truncated, keep
  it false and stop; `cloud_connector.py` refuses to calculate follow-up numbers
  from incomplete context.

Run:

```bash
python cloud_connector.py prepare ../../task-context.json ../../task-items.json
python cloud_connector.py sql ../../task-items.json ../../followup-mutations.sql
```

Apply `followup-mutations.sql`, re-export pending requests so newly queued
follow-ups are included, and rerun `prepare`. Compose every screen decision,
outreach draft, and queued response in the ChatGPT session using
`.claude/agents` and the prompts in `task-items.json`. Do not send anything.
Write `actions.json` with `schema_version: 1`, the unchanged `run_id`, bounded `screens`,
`outreach_drafts`, `request_results`, and one accurate final in-app
`notification`. Validate and render it:

```bash
python cloud_connector.py validate-actions ../../task-items.json ../../actions.json ../../validated-actions.json
python cloud_connector.py sql ../../validated-actions.json ../../action-mutations.sql
```

Apply the transaction through Supabase, then read back the affected IDs and the
new notification. Request updates only affect rows still pending; job messages
upsert on `(scraped_job_id, message_type)`, so retrying does not duplicate them.

## Durable scheduled-task prompt

```text
Run one UAV job-search cycle entirely in ChatGPT Work cloud compute. Use the
connected GitHub and Supabase plugins and current main of
https://github.com/ashishgautam0/UAV. Never use a desktop checkout. Generate one
stable run ID at the start and carry it unchanged through every context, plan,
action, mutation and notification for this run. First check
that no other run of this task is active. Follow CODEX_HOURLY_TASK.md exactly,
including its schema fingerprint, bounded connector exports, cloud_connector.py
file boundary, read-back verification, and stop conditions.

Install backend/requirements.txt in the fresh cloud checkout. Preserve the
existing scraper, title/experience/nationality/resume filters, scoring, 14-day
URL deduplication, Supabase tables, tracked-job-only outreach, follow-up rules,
and message_requests queue. Compose screening decisions and drafts yourself
from the stored profile and repository instructions. Store drafts only. Never
send outreach, email, LinkedIn messages, or applications, and never call an
external LLM API.

Use only Supabase actions actually exposed in this run. Identify the UAV project
by schema before reading task data. Never request, reveal, or store credentials.
Apply only SQL generated by cloud_connector.py and verify affected rows by ID.
Always create the final in-app summary notification. Report web push as
unavailable unless this exact scheduled runtime has a separately verified,
supported signing capability for VAPID; do not claim it ran merely because
VAPID variables exist in Vercel.

Report source counts/errors, new and deduplicated jobs, filter counts,
screen pass/fail counts, stored drafts, fulfilled/failed requests, in-app
notification verification, database read-back results, and push status without
including secrets or full profile text. On any connector, schema, network,
checkout, dependency, SQL, or verification failure, stop before later writes
and report the exact stage.
```

Activation cadence: hourly at minute 59. Preserve the old scheduler timezone
only if it is verified. Otherwise use `Asia/Kolkata` as a newly selected default
and report that distinction when activating.
