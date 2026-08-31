import os
import sys

# Add modules directory to path so existing module imports work unchanged
_modules_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modules")
if _modules_dir not in sys.path:
    sys.path.insert(0, _modules_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import (
    applications,
    company_research,
    follow_ups,
    jd_analyzer,
    messages,
    mini_demos,
    notifications,
    profile,
    referrals,
    scraper,
    stats,
    tonight,
)

# Inject env vars from settings so modules read them via os.environ
settings = get_settings()
for key in ("SUPABASE_URL", "SUPABASE_KEY", "VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY", "VAPID_CLAIM_EMAIL"):
    val = getattr(settings, key, "")
    if val:
        os.environ[key] = val

app = FastAPI(title="Job Search HQ API", version="1.0.0")


@app.get("/api/demo/{job_id}")
def live_demo(job_id: int):
    """Serve the routine-built mini demo for a job as a live HTML page.

    The demo is a self-contained HTML document stored in job_messages
    (message_type='demo_html') — saving it there IS the production deploy.
    """
    from fastapi.responses import HTMLResponse
    from tracker import get_job_message, get_scraped_job

    row = get_job_message(job_id, message_type="demo_html")
    if row and row.get("content"):
        return HTMLResponse(row["content"])

    job = get_scraped_job(job_id)
    label = f"{job['title']} at {job['company']}" if job else f"job #{job_id}"
    return HTMLResponse(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Demo not built yet</title></head>"
        "<body style='font-family:system-ui;display:grid;place-items:center;"
        "min-height:100vh;margin:0;background:#0a0a0a;color:#e5e5e5'>"
        f"<p>The mini demo for <b>{label}</b> hasn't been built yet — "
        "the hourly routine creates it on an upcoming run.</p></body></html>",
        status_code=404,
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    # Also accept this project's Vercel preview/branch deployments
    # (uav-<hash>-....vercel.app, uav-git-<branch>-....vercel.app)
    allow_origin_regex=r"^https://uav-[a-z0-9-]+\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(applications.router, prefix="/api/applications", tags=["Applications"])
app.include_router(stats.router, prefix="/api/stats", tags=["Stats"])
app.include_router(scraper.router, prefix="/api/scraped-jobs", tags=["Scraped Jobs"])
app.include_router(tonight.router, prefix="/api/tonight", tags=["Tonight"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(jd_analyzer.router, prefix="/api/analyze", tags=["JD Analyzer"])
app.include_router(company_research.router, prefix="/api/company-research", tags=["Company Research"])
app.include_router(referrals.router, prefix="/api/referrals", tags=["Referrals"])
app.include_router(mini_demos.router, prefix="/api/demos", tags=["Mini Demos"])
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(follow_ups.router, prefix="/api/follow-ups", tags=["Follow-ups"])


@app.get("/api/vapid-public-key")
def vapid_public_key():
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@app.get("/api/health")
def health():
    return {"status": "ok"}
