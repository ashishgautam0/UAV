# AI Job Application Agent

**Automate the whole job hunt: find AI/ML jobs across 11 portals, apply to them
automatically with Claude Computer Use, then research each employer, build a
working demo for the role, and write the recruiter outreach — all tracked in one
place.**

Built for entry-level AI/ML roles in India. Applies on **LinkedIn, Indeed,
Naukri, Instahyre, Cutshort, Wellfound, Shine, Glassdoor India, FirstNaukri,
Unstop and Apna**, including jobs that hand off to the employer's own site or
ATS (Greenhouse, Lever, Workday, SmartRecruiters, Taleo).

> Keywords: auto apply bot · job application automation · AI job search agent ·
> Claude Computer Use · LinkedIn auto apply · Naukri auto apply · recruiter
> outreach automation · cold DM generator · application tracker · job scraper

---

## What it actually does

```
  You paste one prompt into Claude Desktop
            │
            ▼
  ┌──────────────────────────────┐
  │  Auto-apply agent            │   11 portals, no cap, no time limit
  │  (Claude Computer Use)       │   fills forms, creates accounts, submits
  └──────────────┬───────────────┘   skips anything it cannot answer truthfully
                 │ records every job it handles
                 ▼
  ┌──────────────────────────────┐
  │  Tracker (Supabase)          │   day 1: the job is logged
  └──────────────┬───────────────┘
                 │
                 ▼
  ┌──────────────────────────────┐
  │  Outreach pipeline           │   runs itself every 3 hours
  │  (scheduled Claude routine)  │   research → demo → drafts
  └──────────────┬───────────────┘
                 │
                 ▼
     day 8: HR email + LinkedIn connection note, each with that job's demo
     day 16: one follow-up round, then the record is marked Ghosted
```

### 1. Apply automatically

A single prompt (`prompts/job-agent-desktop.md`) drives Claude Computer Use in
your own browser. It searches each portal, judges every posting against title,
experience and red-flag rules, fills the form from your saved answers and
submits — **without asking permission each time**.

- **No application cap and no time limit.** It works a portal until it runs out,
  moves to the next, then cycles back for new postings.
- **Follows the job off-site.** Most real openings apply on the employer's own
  site or an ATS; it goes there, registers an account if required, and finishes
  the application.
- **Never invents an answer.** If a form asks something your saved answers and
  resume do not cover, it skips that job rather than guessing or stopping to ask.
- **Deduplicates across runs and portals** against a server-side skip list, so
  the same role is never applied to twice.
- **Honours your excluded-companies list.**

### 2. Research, demo and outreach — hands-off

A scheduled Claude routine runs every 3 hours and, for each tracked job:

| Step | What it produces |
|---|---|
| **Screening** | Reads your verified résumé against the JD; dismisses genuine mismatches |
| **Company research** | Official website, a real hiring contact, and the employer's **published** hiring email with the page it came from |
| **Mini demo** | A working, interactive, job-specific demo deployed at `/api/demo/<id>` |
| **Cold DM** | One truthful LinkedIn connection note, under 300 characters |
| **HR email** | A 70–110 word application email carrying that job's demo link |
| **Résumé points** | Tailored bullets and an ATS keyword line for that posting |
| **Follow-ups** | A fresh follow-up when the date arrives — never a "just circling back" |

There is **no LLM API key**. The scheduled session *is* Claude, so it writes
every message itself and stores the drafts.

### 3. Outreach cadence

| Day | What happens |
|---|---|
| **1** | The job enters the tracker |
| **8** | HR email **and** LinkedIn connection note, each with the job's demo |
| **16** | One follow-up round, then the record is marked Ghosted |

The LinkedIn follow-up DM only goes out **if the connection was accepted** —
LinkedIn will not deliver one otherwise. The follow-up email goes regardless.

### 4. Nothing is sent without you

The pipeline **drafts and stores**; it never sends. Sending happens through your
own Gmail and LinkedIn, from a prompt you paste, with a confirmation step before
each send. Connection invitations are capped at 10 per day.

### 5. Tracker and analytics

Application tracker with status funnel, per-platform response rates, weekly
progress against a target, follow-ups due, and versioned PDF résumé profiles
whose extracted facts you review and approve before anything uses them.

---

## Recipient evidence — why emails say "unknown" sometimes

An HR email may only go to an address that is **on record**: one the employer
published on its own careers or contact page (cached with that URL), or one
printed in the job posting itself.

Addresses are **never constructed** — not `firstname.lastname@`, and not
`careers@` assembled from a domain. A draft whose recipient matches no evidence
is rejected when it is saved. When nothing is published, the draft says
`To: unknown — recipient verification required`, which is the honest outcome
rather than a plausible-looking guess.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Auto-apply | Claude Computer Use (Claude Desktop), driven by a markdown prompt |
| Automation | Scheduled Claude Code routine, every 3 hours — no LLM API key |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, shadcn/ui |
| Backend | FastAPI on Vercel serverless |
| Database | Supabase (PostgreSQL, RLS enabled with no policies) |
| Scraping | requests, BeautifulSoup4, python-jobspy |

## Project structure

```
├── prompts/
│   └── job-agent-desktop.md     # THE auto-apply prompt — paste into Claude Desktop
├── .claude/agents/              # One specialist agent per pipeline step
│   ├── resume-screener.md       # résumé vs JD, pass/fail/review
│   ├── job-research.md          # website, hiring contact, published hiring email
│   ├── demo-builder.md          # deploys a job-specific interactive demo
│   ├── cold-dm.md               # LinkedIn connection note
│   ├── recruiter-email.md       # HR email with evidenced recipient
│   ├── resume-tailor.md         # tailored bullets + ATS keywords
│   └── followup.md              # follow-up rounds
├── backend/
│   ├── app/routers/             # FastAPI routes
│   └── modules/
│       ├── tracker.py           # applications, messages, cadence (Supabase)
│       ├── pending_messages.py  # the CLI the routine drives
│       ├── email_finder.py      # harvests published addresses; never guesses
│       ├── outreach_quality.py  # deterministic draft checks
│       └── scraper.py           # job source scrapers
├── frontend/src/app/(app)/      # dashboard · tracker · jobs · settings
└── supabase/schema.sql          # database schema
```

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase project
- Claude Desktop (for the auto-apply agent)

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

Settings holds the generated prompts — the Claude Desktop job search prompt,
the initial HR email, cold DM and HR follow-up prompts, the excluded-company
list, and the résumé profile. None of the prompts are editable in the app: each
ships with the repository, so **Generate** always renders the current version
with your live API links, résumé links and saved answers resolved into it.

Pasting a generated prompt starts browser work in your own session. Login,
sensitive-data approval and the final send still require your confirmation.

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

### Running the auto-apply agent

1. Log into all eleven portals in your browser.
2. **Settings → Claude Desktop job search prompt → Generate prompt → Copy prompt.**
3. Paste it into Claude Desktop (Cowork) and leave it running.

The prompt resolves your live tracker API links, résumé links and excluded
companies at generate time. It is not editable in the app — improvements to the
shipped file reach the agent on the next Generate.

### The scheduled outreach routine

Job discovery and applying belong to the desktop agent. The routine handles
everything *after* a job is tracked, every 3 hours (`59 */3 * * *`): screening,
company research, demos, cold DMs, HR emails, résumé points and follow-ups. It
processes at most 15 items per firing, best-fit first, and a backlog drains over
later runs.

It checks out this repository, installs `backend/requirements.txt`, and drives
the same CLI you can run by hand:

```bash
cd backend/modules
python pending_messages.py list --type hr_email --limit 10   # what needs a draft
python pending_messages.py save --type hr_email --job-id <ID> < message.txt
python pending_messages.py intel --name "<Company>"          # cached research
python pending_messages.py followups                         # queue what is due
python pending_messages.py requests --limit 15               # drain the queue
python pending_messages.py notify --title "..." --body "..." # one push per run
```

That environment needs `SUPABASE_URL` and `SUPABASE_KEY` only. Web push also
needs `VAPID_PRIVATE_KEY` and `VAPID_CLAIM_EMAIL` in the routine's environment
and `VAPID_PUBLIC_KEY` on the API project; without them the in-app notification
still lands and only the push is skipped.

### Excluding companies

Settings → **Exclude companies from scraped jobs**, one employer per line. The
list filters the scraper's intake **and** is written into the desktop prompt, so
the auto-apply agent skips them too. Matching normalises case, punctuation and
common legal suffixes, so `Rivet AI Pvt. Ltd.` matches an entry of `Rivet AI`. A
company merely *mentioned* in a job description is not the employer and does not
trigger it.

## API routes

```
GET/POST /api/applications     # application CRUD
GET      /api/stats            # dashboard analytics
GET      /api/scraped-jobs     # scraped job listings
GET/POST /api/desktop-agent    # skip list + job recording for the auto-apply agent
GET      /api/demos/{id}       # the deployed per-job mini demo
POST     /api/company-research # company research
GET/PUT  /api/profile          # résumé profile, settings, generated prompts
POST     /api/notifications    # web push
GET      /api/health           # health check
```

## Honest limits

- **The auto-apply agent runs in your browser, on your machine.** It cannot be
  scheduled from the cloud — you paste the prompt and it goes. Everything after
  a job is tracked *is* fully automatic.
- **CAPTCHAs end that one application.** The agent does not attempt them and
  never uses a solving service, so postings gated behind one are skipped and
  listed at the end of the run.
- **Nothing is emailed or DM'd automatically.** Drafts are stored; you send them
  through your own accounts with a confirmation step.
- **Portal terms of service vary.** Several job boards restrict automated
  applying. Per-application pauses and a daily invitation cap are built in, but
  you are responsible for how you use this against a given site's rules.
- Résumé matching is deterministic and evidence-oriented — not an ATS
  certification. Scanned or image-only PDFs are rejected because OCR is not
  available, and anything ambiguous is surfaced for review rather than guessed.

## Licence

No licence file is present, so the default applies: all rights reserved. Open an
issue if you would like to use it.
