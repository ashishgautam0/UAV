# Job Search HQ

A full-stack AI-powered job search automation platform for AI/ML roles. Combines intelligent LinkedIn job scraping, LLM-generated personalized outreach, application tracking, and analytics — with hourly automated runs via GitHub Actions.

## Features

### Job Scraper
- Scrapes **LinkedIn** via JobSpy across 24 AI/ML search queries × 2 locations (India, Remote)
- Filters by AI/ML keywords, role level, and location
- LLM-powered relevance scoring (0–100) using Groq
- Deduplication and company blacklist filtering

### AI Message Generator
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

### Hourly Automation
- GitHub Actions workflow runs every hour
- Scrapes all sources, scores and ranks jobs
- Sends formatted HTML email summary
- Saves results to Supabase

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
| AI/LLM | Groq (llama-3.3-70b-versatile) |
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
│       ├── hourly.py            # Hourly automation script
│       ├── jd_analyzer.py       # Job description analysis
│       ├── resume_tailor.py     # Resume tailoring
│       ├── company_research.py  # Company research & caching
│       └── send_email.py        # Email notifications
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
└── .github/workflows/
    └── nightly.yml              # Hourly scraper cron job
```

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase project
- Groq API key

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
GROQ_API_KEY=your_groq_api_key
GMAIL_ADDRESS=your_email          # For email notifications
GMAIL_APP_PASSWORD=your_app_pass  # Gmail app password
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

- **API project** — `SUPABASE_URL`, `SUPABASE_KEY`, `GROQ_API_KEY`,
  `APP_USERNAME`, `APP_PASSWORD`, `JWT_SECRET`, and `FRONTEND_URL` (so CORS
  allows the frontend origin). `OPENAI_API_KEY`, `GMAIL_ADDRESS`,
  `GMAIL_APP_PASSWORD` and the `VAPID_*` keys are optional — see
  `backend/app/config.py`.
- **Frontend project** — `NEXT_PUBLIC_API_URL`, set to the API project's URL.
  This is read at build time (`frontend/src/lib/api.ts` falls back to
  `http://localhost:8000`), so set it **before** the first build, or redeploy
  after adding it.

The hourly scraper runs from `.github/workflows/nightly.yml`, which is
`workflow_dispatch`-only — trigger it from the Actions tab or an external cron
service. It needs the same secrets set on the repository.

## API Routes

```
GET/POST /api/applications    # Application CRUD
GET      /api/stats           # Dashboard analytics
GET      /api/scraped-jobs    # Scraped job listings
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
