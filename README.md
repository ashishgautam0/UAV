# Job Search HQ

A full-stack AI-powered job search automation platform for AI/ML roles. Combines intelligent LinkedIn job scraping, LLM-generated personalized outreach, application tracking, and analytics — with hourly automated runs via GitHub Actions.

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
- **Cover Letters** — Under 200 words, personalized
- **Thank You Notes** — Post-interview, referencing discussion points
- **Referral Requests** — Templates for warm intros
- **Demo Outreach** — Messages showcasing custom demo projects

### Application Tracker
- Log applications with metadata: company, role, platform, status, date, follow-up reminders
- Track job type, platform source, NOC compatibility, conversion potential, salary
- Auto-set 7-day follow-up reminders
- Filter by status, type, and platform

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
- Sort by relevance score, source, or company
- Quick-apply button to log applications directly

### Daily Automation
- A scheduled Claude routine runs the scraper once a day at 18:00 IST
- Scrapes LinkedIn, filters and deduplicates against previous runs
- Saves new jobs and a markdown digest to Supabase
- Writes a cold outreach DM for each new job — the routine session is Claude, so
  it composes them itself and stores them in `job_messages`. No LLM API key.
- Raises an in-app notification and a web push

### Additional Tools
- **JD Analyzer** — NOC compatibility check, skill match scoring, red flag detection, ATS compatibility
- **Resume Tailor** — Project ordering, skill prioritization, gap analysis based on JD
- **Company Research** — Web search with result caching
- **Referral Manager** — Track referral contacts and follow-ups
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
| Automation | GitHub Actions (hourly cron) |
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
│       ├── hourly.py            # Daily automation script
│       ├── jd_analyzer.py       # Job description analysis
│       ├── resume_tailor.py     # Resume tailoring
│       ├── company_research.py  # Company research & caching
│       ├── pending_messages.py  # CLI the Claude routine drives to write DMs
│       └── digest.py            # Markdown digest builder
├── frontend/
│   └── src/app/
│       ├── (app)/
│       │   ├── dashboard/       # Analytics dashboard
│       │   ├── tonight/         # Tonight's Plan view
│       │   ├── tracker/         # Application tracker
│       │   ├── messages/        # AI message generator
│       │   ├── analyzer/        # JD analyzer
│       │   ├── resume-tailor/   # Resume tailor
│       │   ├── referrals/       # Referral manager
│       │   ├── links/           # Quick links
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

That creates all 10 tables the backend expects (`applications`, `scraped_jobs`,
`referrals`, `follow_up_history`, `company_research_cache`, `mini_demos`,
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
  allows the frontend origin). `OPENAI_API_KEY` and the `VAPID_*` keys are
  optional — see `backend/app/config.py`.
- **Frontend project** — `NEXT_PUBLIC_API_URL`, set to the API project's URL.
  This is read at build time (`frontend/src/lib/api.ts` falls back to
  `http://localhost:8000`), so set it **before** the first build, or redeploy
  after adding it.

### Scheduled scraping

The scraper is not triggered by the deployed API — a full run makes 48 LinkedIn
queries with pauses between them, far longer than a serverless function may run.
It is instead executed once a day at 18:00 IST (12:30 UTC) by a scheduled
Claude routine, which
checks out this repository, installs `backend/requirements.txt`, and runs:

```bash
cd backend/modules && python hourly.py
```

It then writes the outreach messages itself — there is no hosted LLM call in
this path. The routine lists jobs with no message yet, composes one per job, and
saves it:

```bash
python pending_messages.py list --limit 10
python pending_messages.py save --job-id <ID> < message.txt
```

It also drains the freeform queue. Anything requested from the Messages or
Referrals page lands in `message_requests`; the routine renders each request
back into the prompt the app would have sent and answers it:

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

## API Routes

```
GET/POST /api/applications    # Application CRUD
GET      /api/stats           # Dashboard analytics
GET      /api/scraped-jobs    # Scraped job listings
GET      /api/scraped-jobs/{id}/message  # Routine-written outreach message
GET      /api/messages/requests   # Queued message requests
GET      /api/messages/requests/{id}  # Poll one queued request
GET      /api/tonight         # Tonight's Plan jobs
POST     /api/messages        # AI message generation
POST     /api/analyze         # JD analysis
POST     /api/resume-tailor   # Resume tailoring
POST     /api/company-research # Company research
GET/POST /api/referrals       # Referral tracking
GET/POST /api/demos           # Mini demo projects
GET/PUT  /api/profile         # User profile
POST     /api/notifications   # Push notifications
GET      /api/health          # Health check
```
