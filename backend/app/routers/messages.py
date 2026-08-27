"""Message generation, served as a queue.

These routes used to call a hosted LLM and return the text inline. They now
park the request in Supabase and return `content: null` with a `request_id`;
the scheduled Claude routine writes the message and marks the request ready.
The request bodies are unchanged, so the UI keeps posting exactly what it did.
"""

from fastapi import APIRouter, HTTPException, status

from ..models.schemas import (
    ColdDMRequest,
    CoverLetterRequest,
    DemoOutreachRequest,
    FollowUpRequest,
    ReferralRequestBody,
    ThankYouRequest,
)
from tracker import (
    create_message_request,
    get_message_request,
    get_message_requests,
)

router = APIRouter()


def _queue(message_type: str, params: dict):
    """Queue a request and shape it like the old inline response."""
    row = create_message_request(message_type, params)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not queue the message request.",
        )
    return {
        "request_id": row["id"],
        "status": row.get("status", "pending"),
        # null until the routine writes it — the UI treats this as "queued"
        "content": None,
    }


@router.get("/requests")
def list_requests(status: str | None = None, limit: int = 50):
    """Recent message requests, newest first."""
    return get_message_requests(status=status, limit=limit)


@router.get("/requests/{request_id}")
def read_request(request_id: int):
    """Poll one request. 404 only when the id genuinely does not exist."""
    row = get_message_request(request_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Request not found")
    return row


@router.post("/cold-dm")
def cold_dm(body: ColdDMRequest):
    return _queue("cold-dm", {
        "company_name": body.company,
        "role_title": body.role,
        "company_description": body.company_desc,
        "platform": body.platform,
        "project_link": body.project_link,
    })


@router.post("/follow-up")
def follow_up(body: FollowUpRequest):
    return _queue("follow-up", {
        "company_name": body.company,
        "role_title": body.role,
        "days_since_applied": body.days,
        "original_platform": body.platform,
        "follow_up_number": body.follow_up_number,
        "previous_messages": body.previous_messages,
    })


@router.post("/cover-letter")
def cover_letter(body: CoverLetterRequest):
    return _queue("cover-letter", {
        "company_name": body.company,
        "role_title": body.role,
        "job_description": body.jd,
        "company_info": body.company_info,
    })


@router.post("/thank-you")
def thank_you(body: ThankYouRequest):
    return _queue("thank-you", {
        "company_name": body.company,
        "interviewer_name": body.interviewer,
        "key_discussion_point": body.discussion,
    })


@router.post("/referral-request")
def referral_request(body: ReferralRequestBody):
    return _queue("referral-request", {
        "contact_name": body.contact_name,
        "contact_role": body.contact_role,
        "company": body.company,
        "role_applying_for": body.role_applying_for,
        "relationship": body.relationship,
    })


@router.post("/demo-outreach")
def demo_outreach(body: DemoOutreachRequest):
    return _queue("demo-outreach", {
        "company": body.company,
        "role": body.role,
        "demo_url": body.demo_url,
        "demo_description": body.demo_description,
        "company_desc": body.company_desc,
    })
