from fastapi import APIRouter, HTTPException, Query

from ..models.schemas import MarkScrapedJobRequest
from tracker import (
    delete_scraped_job,
    find_scraped_job_by_url,
    get_job_message,
    get_scraped_job,
    get_scraped_jobs,
    mark_scraped_job,
)

router = APIRouter()


@router.get("")
def list_scraped_jobs(
    source: str | None = None,
):
    df = get_scraped_jobs(source=source)
    return df.to_dict("records") if not df.empty else []


@router.get("/lookup")
def lookup_scraped_job(url: str = Query(...)):
    """Resolve a posting URL to its scraped job id (e.g. from a tracker row)."""
    row = find_scraped_job_by_url(url)
    return {"id": row["id"] if row else None}


@router.get("/{job_id}")
def get_one_scraped_job(job_id: int):
    """One scraped job by id, regardless of applied/dismissed state."""
    row = get_scraped_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return row


@router.delete("/{job_id}")
def delete_one_scraped_job(job_id: int):
    """Permanently delete a scraped job and its stored messages."""
    if not delete_scraped_job(job_id):
        raise HTTPException(status_code=500, detail="Delete failed")
    return {"success": True}


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
