"""Endpoints the Claude Desktop Computer Use agent calls while it applies.

The agent runs in the user's own browser, so it reaches these over HTTPS rather
than importing the modules directly. Two things it needs from the backend: the
set of postings already dealt with (so repeat runs skip them) and a way to
record a job it just handled into both the job list and the Tracker.
"""

from fastapi import APIRouter

from ..models.schemas import DesktopAgentJobRequest
from tracker import (
    add_application,
    find_application_by_url,
    find_scraped_job_by_url,
    get_handled_job_urls,
    mark_scraped_job,
    save_scraped_job,
)

router = APIRouter()


@router.get("/seen-urls", name="desktop_agent_seen_urls")
def seen_urls():
    """Posting URLs already applied to or dismissed, for the agent's skip list.

    Deliberately excludes postings that are merely present and unhandled, such
    as the rows the removed job scraper left behind: those were never applied
    to, so applying to them is still the agent's job.
    """
    urls = get_handled_job_urls()
    return {"urls": sorted(urls), "count": len(urls)}


@router.post("/jobs", name="desktop_agent_record_job")
def record_job(body: DesktopAgentJobRequest):
    """Record a handled posting, whichever portal it came from.

    Applied postings reach the Tracker. Skipped ones are dismissed, which both
    hides them and puts them on the next run's skip list.
    """
    # Only insert a posting no row already holds. save_scraped_job overwrites
    # the whole row, which on a known job would replace the full JD with the
    # agent's summary, wipe any score and analysis already on it, and mark its
    # cover letter outdated.
    scraped = find_scraped_job_by_url(body.url)
    if not scraped:
        save_scraped_job(
            title=body.title,
            company=body.company,
            location=body.location,
            source=body.source,
            url=body.url,
            description=body.description,
        )
        scraped = find_scraped_job_by_url(body.url)

    if body.status == "skipped":
        if scraped:
            mark_scraped_job(scraped["id"], "dismissed")
        return {"saved": True, "applied": False, "dismissed": bool(scraped), "duplicate": False}

    # A posting the user already applied to must not produce a second Tracker
    # row; the agent can re-send the same job after an interrupted run.
    if find_application_by_url(body.url):
        return {"saved": True, "applied": False, "dismissed": False, "duplicate": True}

    add_application(
        company=body.company,
        role=body.title,
        job_type=body.job_type,
        platform=body.source,
        url=body.url,
        notes=body.notes,
    )
    if scraped:
        mark_scraped_job(scraped["id"], "applied")
    return {"saved": True, "applied": True, "dismissed": False, "duplicate": False}
