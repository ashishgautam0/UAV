import re

from fastapi import APIRouter, HTTPException, Query

from ..models.schemas import MarkScrapedJobRequest
from tracker import (
    _get_client,
    delete_scraped_job,
    find_scraped_job_by_url,
    get_job_message,
    get_scraped_job,
    get_scraped_jobs,
    mark_scraped_job,
)

router = APIRouter()


def _profile_text():
    try:
        from message_generator import _get_profile_text
        return _get_profile_text()
    except Exception:
        return ""


def _eval_scores(job_ids):
    """Map job id -> A–H fit score (float 1..5) parsed from the stored
    `evaluation` message, for the given ids. Missing/unparseable are omitted."""
    if not job_ids:
        return {}
    out = {}
    db = _get_client()
    for i in range(0, len(job_ids), 100):
        chunk = job_ids[i:i + 100]
        try:
            resp = (db.table("job_messages")
                    .select("scraped_job_id, content")
                    .eq("message_type", "evaluation")
                    .in_("scraped_job_id", chunk)
                    .execute())
        except Exception:
            continue
        for row in resp.data or []:
            m = re.search(r"fit\s*score:\s*([\d.]+)", row.get("content") or "", re.I)
            if m:
                try:
                    out[row["scraped_job_id"]] = float(m.group(1))
                except ValueError:
                    pass
    return out


@router.get("")
def list_scraped_jobs(
    source: str | None = None,
):
    df = get_scraped_jobs(source=source)
    return df.to_dict("records") if not df.empty else []


@router.get("/ranked")
def ranked_scraped_jobs(limit: int = 200):
    """Scraped jobs ordered by BestScore — the queue to apply to, best first.

    Each row gains `bestscore` (0–100) and a `bestscore_breakdown`. Computed
    live from existing columns + any cached A–H evaluations.
    """
    from ranking import rank_jobs

    df = get_scraped_jobs()
    jobs = df.to_dict("records") if not df.empty else []
    if not jobs:
        return []
    scores = _eval_scores([j["id"] for j in jobs if j.get("id") is not None])
    return rank_jobs(jobs, profile_text=_profile_text(), eval_scores=scores)[:limit]


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
