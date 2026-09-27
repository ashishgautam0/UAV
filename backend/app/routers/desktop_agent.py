"""Endpoints the Claude Desktop Computer Use agent calls while it applies.

The agent runs in the user's own browser, so it reaches these over HTTPS rather
than importing the modules directly. Two things it needs from the backend: the
set of postings already seen (so repeat runs skip them) and a way to record a
job it just handled into both the job list and the Tracker.
"""

from fastapi import APIRouter, Query

from ..models.schemas import DesktopAgentJobRequest
from tracker import (
    add_application,
    dedup_window_days,
    find_application_by_url,
    get_existing_job_urls,
    save_scraped_job,
)

router = APIRouter()


@router.get("/seen-urls", name="desktop_agent_seen_urls")
def seen_urls(days: int | None = Query(None, ge=1, le=365)):
    """Posting URLs already recorded, using the scraper's dedup window.

    The agent fetches this once per run and skips any posting whose URL is in
    the list, which is what keeps the same jobs from resurfacing every run.
    """
    window = days or dedup_window_days()
    urls = get_existing_job_urls(since_days=window)
    return {"urls": sorted(urls), "count": len(urls), "window_days": window}


@router.post("/jobs", name="desktop_agent_record_job")
def record_job(body: DesktopAgentJobRequest):
    """Save a handled posting to the job list, and to the Tracker if applied."""
    save_scraped_job(
        title=body.title,
        company=body.company,
        location=body.location,
        source=body.source,
        url=body.url,
        description=body.description,
    )

    if body.status != "applied":
        return {"saved": True, "applied": False, "duplicate": False}

    # A posting the user already applied to must not produce a second Tracker
    # row; the agent can re-send the same job after an interrupted run.
    if find_application_by_url(body.url):
        return {"saved": True, "applied": False, "duplicate": True}

    add_application(
        company=body.company,
        role=body.title,
        job_type=body.job_type,
        platform=body.source,
        url=body.url,
        notes=body.notes,
    )
    return {"saved": True, "applied": True, "duplicate": False}
