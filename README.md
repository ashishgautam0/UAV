# Job Search HQ

A full-stack AI-powered job search automation platform for AI/ML roles. Combines intelligent LinkedIn job scraping, LLM-generated personalized outreach, application tracking, and analytics — with hourly automated runs via a scheduled Claude routine.

## Features

### Job Scraper
- Scrapes **LinkedIn** via JobSpy across 24 AI/ML search queries × 2 locations (India, Remote)
- Filters by AI/ML keywords, role level, and location
- Deduplication and company blacklist filtering

### AI Message Generator
- No LLM API key: every message is written by the scheduled Claude routine
- Requests queued from the UI are fulfilled on the next hourly run
- **Cold DMs** — 2 variants per company (direct + curiosity-driven)
- **Follow-ups** — Value-add messages, not generic check-ins
- **Cover Letters** — Under 200 words, personalized; audited drafts for
  explicitly eligible high-match jobs are versioned and provenance-tracked
- **Thank You Notes** — Post-interview, referencing discussion points
- **Demo Outreach** — Messages showcasing custom demo projects

### Application Tracker
- Log applications with metadata: company, role, platform, status, date, follow-up reminders
- Track job type, platform source, regional annotations, conversion potential, salary
- PDF-only, versioned resume profiles with reviewed facts and evidence
- Separate document readability, mandatory eligibility, resume–JD match, and application priority
- Audited cover-letter drafts for explicitly eligible high-match jobs (configurable, default 90)
- Auto-set 7-day follow-up reminders
- Filter by status, type, and platform

Matching is deterministic and evidence-oriented, not a universal ATS
certification or a claim of market superiority. Scanned/image-only PDFs are
rejected because OCR is not available; incomplete extraction, ambiguous dates,
and unknown mandatory criteria are surfaced for review rather than guessed.

### Analytics Dashboard
- Weekly progress tracking (target: 50 applications/week)
- Follow-up reminders widget
- Platform effectiveness comparison
- Response rate analytics by platform
- Job vs internship split
- Status funnel (applied → interview → offer)

### Tonight's Plan
- View scraped jobs from the past 24 hours
- Filter by work mode (remote/hybrid/onsite)
- Show saved jobs newest-first, with optional work-mode filtering
- Quick-apply button to log applications directly

### Hourly Automation
- A scheduled Claude routine runs the scraper every hour (`59 * * * *`)
- Scrapes LinkedIn, filters and deduplicates against previous runs
- Saves new jobs and a markdown digest to Supabase
- Writes a cold outreach DM for each new job — the routine session is Claude, so
  it composes them itself and stores them in `job_messages`. No LLM API key.
- Raises an in-app notification and a web push

### Additional Tools
- **Company Research** — Web search with result caching
- **Mini Demos** — Track custom demo projects for target companies

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript |
| Styling | Tailwind CSS 4, shadcn/ui, Lucide icons |
| Backend | FastAPI, Uvicorn |
| AI/LLM | Claude, via the scheduled routine (no API key) |
| Database | Supabase (PostgreSQL) |
| Scraping | requests, BeautifulSoup4, python-jobspy |
| Automation | Scheduled Claude routine (hourly cron) |
| Deployment | Vercel (frontend) |

## Project Structure

```
job_search_tool/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings & environment config
│   │   ├── routers/             # API route handlers
│   │   └── models/              # Pydantic schemas
│   └── modules/
│       ├── scraper.py           # 12+ job source scrapers
│       ├── message_generator.py # LLM-powered message generation
│       ├── tracker.py           # Application tracking (Supabase)
│       ├── hourly.py            # Hourly automation script
│       ├── jd_analyzer.py       # Job description analysis
│       ├── company_research.py  # Company research & caching
│       ├── pending_messages.py  # CLI the Claude routine drives to write DMs
│       └── digest.py            # Markdown digest builder
├── frontend/
│   └── src/app/
│       ├── (app)/
│       │   ├── dashboard/       # Analytics dashboard
│       │   ├── tonight/         # Tonight's Plan view
│       │   ├── tracker/         # Application tracker
│       │   ├── prep28/          # Interview prep plan
│       │   └── settings/        # Settings
│       └── page.tsx             # Landing page
└── supabase/
    └── schema.sql               # Database schema
```

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase project

### Database

Create a Supabase project, then apply the schema once:

Supabase dashboard -> **SQL Editor** -> **New query** -> paste [`supabase/schema.sql`](supabase/schema.sql) -> **Run**.

That creates the tables the backend expects (`applications`, `scraped_jobs`,
`follow_up_history`, `company_research_cache`, `mini_demos`,
`email_logs`, `notifications`, `push_subscriptions`, `user_profile`) with their
indexes, and enables Row Level Security on each.

RLS is enabled with **no policies**, so anon and authenticated keys are denied
everything and only the `service_role` key reaches the data. The frontend never
talks to Supabase directly — it calls the FastAPI backend — so set `SUPABASE_KEY`
to the **service_role** key on the backend and keep it out of the browser.

### Backend

```bash
cd backend
pip install -r requirements.txt

# Create .env file
cp .env.example .env  # or create manually
```

Required environment variables:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_role_key  # service_role: RLS is on with no policies
```

Optional:

```env
FRONTEND_URL=https://your-frontend.vercel.app
CORS_ORIGINS=https://your-domain.com
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:3000` and the backend on `http://localhost:8000`.

The Settings page stores the editable Today Todo browser-agent template and
application answers in the backend. Its **Ready-to-paste Codex prompt** is
rendered from the current Today Todo rows plus the latest Settings PDF, with a
fixed job ID/URL batch. Copying remains disabled when the resume, jobs,
submission authorization, or a supported placeholder is missing. Pasting the
rendered prompt starts the supported browser work, but login, CAPTCHA,
sensitive-data approval, missing truthful answers, and final third-party
submission can still require user confirmation.

The generated prompt uses Dashboard's Company HR email todos as the email queue,
including previously tracked jobs outside the application batch. It opens each
todo's linked Tracker detail instead of scanning company details or all Tracker
records, and returns to Dashboard to verify completion and process the next todo.
It uses the stored draft's To/Subject/body, verifies the hiring
contact and live mini-demo link, and attaches the actual latest Settings PDF.
Missing drafts/demos or mail access are reported as blocked/pending, not sent.
Codex must request confirmation immediately before sending, check Sent mail to
avoid duplicates, and mark the HR todo complete only after verified sending.
This is a prompt-driven mail-client workflow, not a background email service;
the Claude routine still only stores drafts and no schedule is changed.

The prompt also processes Dashboard's **Follow-ups Due** queue through each
linked Tracker detail. It checks dates/history, uses the current numbered draft,
requires confirmation before sending, and records the exact sent message/channel
with **Record sent follow-up** only after verified delivery to the mail provider.
Missing drafts are pending; future dates and follow-ups immediately after a new
HR email are deferred. Initial HR completion and follow-up history stay separate.
The recording control checks existing history and locks after an uncertain write;
it is not a database-level concurrency guarantee across multiple browser sessions.

## Deployment

The repo deploys as **two Vercel projects from this one repository**, plus the
Supabase project above.

| Project | Root Directory | Framework |
| --- | --- | --- |
| Frontend | `frontend` | Next.js (auto-detected) |
| API | *(repository root)* | Python; `vercel.json` rewrites `/api/(.*)` to `api/index.py` |

At [vercel.com/new](https://vercel.com/new), import the repository twice and set
the Root Directory as above.

Environment variables:

- **API project** — `SUPABASE_URL`, `SUPABASE_KEY`,
  `APP_USERNAME`, `APP_PASSWORD`, `JWT_SECRET`, and `FRONTEND_URL` (so CORS
  allows the frontend origin). The `VAPID_*` keys are optional (they enable
  web-push notifications) — see `backend/app/config.py`. `PUBLIC_API_URL` is
  optional and overrides the public API origin embedded in generated mini-demo
  links (the current production API is used by default).
- **Frontend project** — `NEXT_PUBLIC_API_URL`, set to the API project's URL.
  This is read at build time (`frontend/src/lib/api.ts` falls back to
  `http://localhost:8000`), so set it **before** the first build, or redeploy
  after adding it.

### Scheduled scraping

The scraper is not triggered by the deployed API — a full run makes 48 LinkedIn
queries with pauses between them, far longer than a serverless function may run.
It is instead executed every hour by a scheduled Claude routine (`59 * * * *`),
which checks out this repository, installs `backend/requirements.txt`, and runs:

```bash
cd backend/modules && python hourly.py
```

It then writes the outreach messages itself — there is no hosted LLM call in
this path. The routine lists jobs with no message yet, composes one per job, and
saves it:

```bash
python pending_messages.py list --limit 10
python pending_messages.py save --job-id <ID> < message.txt

# tracked jobs that need the one-time Company HR email draft
python pending_messages.py list --type hr_email --limit 10
python pending_messages.py save --type hr_email --job-id <ID> < message.txt
```

Each candidate includes a purpose-specific `draft_spec`. Follow it alongside
`.claude/agents/cold-dm.md` and `.claude/agents/recruiter-email.md`, using the
active verified PDF profile and exact JD. Cold DMs are single LinkedIn connection
notes: target 180–260 characters, maximum 300, one truthful hook and an invitation
to connect. They do not need a demo or claim attachments. Direct save and queued
fulfil reject long/variant drafts; rewrite rather than truncate. Research and
cold notes can proceed before demo creation; HR emails follow the demo.
The Claude routine stores drafts only and does not send outreach.
The user-run cold-DM prompt starts from Dashboard **Follow-ups Due**, not from
all newly tracked jobs. A confirmed LinkedIn invitation with its note is recorded
in Tracker as **LinkedIn connection** using **Record sent follow-up**, advancing
one existing cadence slot (days 7/14/21 from application). Blocked, future,
already-pending or uncertain sends do not advance it. Recording is available
without an email follow-up draft. Existing history/status writes are separate;
after uncertain logging, inspect both and do not blindly record twice.

HR email candidates are emitted only after the job is in Tracker and its mini
demo is live. Each brief stored draft must include that demo URL and say that
the latest Settings PDF is attached. The app still does not send email; the
user's separate Gmail workflow verifies the recipient and attaches the PDF
before sending it. Use an evidenced hiring address or an explicit unknown
recipient marker, never guessed email patterns. Body target: 70–110 words,
one JD-to-profile connection and one request, at most 150 words total.
Merging these instructions does not prove the saved Claude schedule has loaded
them or that a scheduled drafting run has executed.

It also drains the freeform queue. Anything parked in `message_requests` is
rendered back into the prompt the app would have sent, and the routine answers it:

```bash
python pending_messages.py requests
python pending_messages.py fulfil --request-id <ID> < message.txt
```

Each run ends with a summary notification — saved in-app and pushed to every
device subscribed through the installed PWA:

```bash
python pending_messages.py notify --title "Job scan" --body "3 new jobs, 3 DMs"
```

Web push needs `VAPID_PRIVATE_KEY` and `VAPID_CLAIM_EMAIL` in the routine's
environment, and `VAPID_PUBLIC_KEY` on the API project (the bell icon in the
app uses it to subscribe the device). Without them the push is skipped and the
in-app notification still lands.

That environment needs `SUPABASE_URL` and `SUPABASE_KEY` only.

Audited cover-letter drafts for explicitly eligible, high-match jobs follow the
same interface — a queue command, then a save that re-derives the resume/JD
provenance from the live row rather than trusting the caller:

```bash
python pending_messages.py cover-letter-list --limit 10
python pending_messages.py save-cover-letter --job-id <ID> < letter.txt
```

## API Routes

```
GET/POST /api/applications    # Application CRUD
GET      /api/stats           # Dashboard analytics
GET      /api/scraped-jobs    # Scraped job listings
GET      /api/scraped-jobs/{id}/message  # Routine-written outreach message
GET      /api/tonight         # Tonight's Plan jobs
POST     /api/company-research # Company research
GET/PUT  /api/prep28          # 28-day prep progress
GET/POST /api/demos           # Mini demo projects
GET/PUT  /api/profile         # User profile
POST     /api/notifications   # Push notifications
GET      /api/health          # Health check
```
