from fastapi import APIRouter

from ..models.schemas import MarkScrapedJobRequest
from tracker import get_job_message, get_scraped_jobs, mark_scraped_job

router = APIRouter()


@router.get("")
def list_scraped_jobs(
    source: str | None = None,
):
    df = get_scraped_jobs(source=source)
    return df.to_dict("records") if not df.empty else []


@router.patch("/{job_id}")
def mark_job(
    job_id: int,
    body: MarkScrapedJobRequest,
):
    mark_scraped_job(job_id, body.action)
    return {"success": True}


@router.get("/{job_id}/message")
def job_message(
    job_id: int,
    type: str = "cold_dm",
):
    """Outreach message pre-written for this job by the scheduled Claude routine.

    Returns {"content": null} when the routine has not written one yet, rather
    than 404 — the UI treats "not generated yet" as a normal state.
    """
    row = get_job_message(job_id, message_type=type)
    if not row:
        return {"job_id": job_id, "message_type": type, "content": None}
    return {
        "job_id": job_id,
        "message_type": row.get("message_type"),
        "content": row.get("content"),
        "generated_by": row.get("generated_by"),
        "generated_at": row.get("generated_at"),
    }
