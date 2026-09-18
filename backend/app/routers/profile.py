from io import BytesIO
import re

from fastapi import APIRouter, File, HTTPException, UploadFile
from pypdf import PdfReader

from ..models.schemas import (
    ResumeProfileResponse,
    ResumeProfileReviewRequest,
    ResumeProfileStatusResponse,
    UserProfileRequest,
    UserProfileResponse,
)
from profile import (
    activate_resume_profile,
    create_resume_profile,
    get_active_profile_snapshot,
    get_latest_profile_snapshot,
    get_profile,
    get_resume_profile,
    upsert_profile,
)
from resume_profile import extract_profile_facts, reviewed_experience_months

router = APIRouter()

_DEFAULT_USERNAME = "subidh"
_MAX_RESUME_BYTES = 10 * 1024 * 1024
_MAX_RESUME_PAGES = 30


@router.get("/", response_model=UserProfileResponse)
def read_profile():
    data = get_profile(_DEFAULT_USERNAME)
    if data is None:
        return UserProfileResponse(username=_DEFAULT_USERNAME)
    return UserProfileResponse(**data)


@router.put("/", response_model=UserProfileResponse)
def update_profile(body: UserProfileRequest):
    payload = body.model_dump(exclude_none=True)
    saved = upsert_profile(_DEFAULT_USERNAME, payload)
    if saved:
        return UserProfileResponse(**saved)
    return UserProfileResponse(username=_DEFAULT_USERNAME)


def _public_snapshot(snapshot):
    if not snapshot:
        return None
    return {key: value for key, value in snapshot.items() if key not in {"raw_text", "corrections"}}


def _clean_text(value, maximum=500):
    value = str(value or "").strip()
    if len(value) > maximum or any(ord(ch) < 32 and ch not in "\n\r\t" for ch in value):
        raise HTTPException(status_code=422, detail="A reviewed field contains invalid text.")
    return value


def _review_corrections(row, body):
    extracted = ((row.get("extracted_facts") or {}).get("facts") or {})
    evidence_by_id = {}
    for group in ("experience", "education"):
        for item in extracted.get(group) or []:
            if item.get("id"):
                evidence_by_id[item["id"]] = item.get("evidence") or []
    skill_evidence = {
        str(item.get("name", "")).casefold(): item.get("evidence") or []
        for item in extracted.get("skills") or []
    }
    cert_evidence = {
        str(item.get("name", "")).casefold(): item.get("evidence") or []
        for item in extracted.get("certifications") or []
    }

    skills = []
    seen = set()
    for value in body.skills:
        name = _clean_text(value, 120)
        key = name.casefold()
        if not name or key in seen:
            continue
        seen.add(key)
        skills.append({
            "name": name,
            "evidence": skill_evidence.get(key) or [{
                "source": "user_review", "line": None,
                "excerpt": "User-confirmed structured correction",
            }],
        })

    experience = []
    for index, item in enumerate(body.experience):
        value = item.model_dump()
        item_id = _clean_text(value.get("id"), 100) or f"reviewed-experience-{index + 1}"
        start = _clean_text(value.get("start"), 20)
        end = _clean_text(value.get("end"), 20).lower()
        month_pattern = r"(?:19|20)\d{2}-(?:0[1-9]|1[0-2])"
        if not re.fullmatch(month_pattern, start) or not (
            re.fullmatch(month_pattern, end) or end == "present"
        ):
            raise HTTPException(status_code=422, detail="Experience dates must be YYYY-MM or present.")
        experience.append({
            "id": item_id,
            "label": _clean_text(value.get("label"), 300),
            "role": _clean_text(value.get("role"), 200),
            "company": _clean_text(value.get("company"), 200),
            "start": start,
            "end": end,
            "evidence": evidence_by_id.get(item_id) or [{
                "source": "user_review", "line": None,
                "excerpt": "User-confirmed structured correction",
            }],
        })

    education = []
    allowed_levels = {"diploma", "bachelor", "master", "doctorate"}
    for index, item in enumerate(body.education):
        value = item.model_dump()
        level = _clean_text(value.get("level"), 30).lower()
        if level not in allowed_levels:
            raise HTTPException(status_code=422, detail="Invalid education level.")
        item_id = _clean_text(value.get("id"), 100) or f"reviewed-education-{index + 1}"
        education.append({
            "id": item_id, "level": level,
            "credential": _clean_text(value.get("credential"), 300),
            "field": _clean_text(value.get("field"), 200),
            "institution": _clean_text(value.get("institution"), 200),
            "evidence": evidence_by_id.get(item_id) or [{
                "source": "user_review", "line": None,
                "excerpt": "User-confirmed structured correction",
            }],
        })

    certifications = []
    seen = set()
    for value in body.certifications:
        name = _clean_text(value, 300)
        key = name.casefold()
        if not name or key in seen:
            continue
        seen.add(key)
        certifications.append({
            "name": name,
            "evidence": cert_evidence.get(key) or [{
                "source": "user_review", "line": None,
                "excerpt": "User-confirmed structured correction",
            }],
        })
    total_months = reviewed_experience_months(experience)
    if total_months is None and extracted.get("experience_claims"):
        total_months = extracted.get("total_experience_months")
    return {
        "skills": skills,
        "experience": experience,
        "total_experience_months": total_months,
        "education": education,
        "certifications": certifications,
    }


@router.get("/resume", response_model=ResumeProfileStatusResponse)
def resume_status():
    active = get_active_profile_snapshot(_DEFAULT_USERNAME)
    latest = get_latest_profile_snapshot(_DEFAULT_USERNAME)
    return {"active": _public_snapshot(active), "latest": _public_snapshot(latest)}


@router.post("/resume", response_model=ResumeProfileResponse)
async def upload_resume(file: UploadFile = File(...)):
    """Extract a text-based PDF into a pending, evidence-backed profile."""
    filename = file.filename or ""
    if file.content_type != "application/pdf" or not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Please upload a PDF file.")

    raw = await file.read(_MAX_RESUME_BYTES + 1)
    await file.close()
    if len(raw) > _MAX_RESUME_BYTES:
        raise HTTPException(status_code=413, detail="Resume PDF must be 10 MB or smaller.")
    if not raw.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="The selected file is not a valid PDF.")

    try:
        reader = PdfReader(BytesIO(raw))
        if len(reader.pages) > _MAX_RESUME_PAGES:
            raise HTTPException(
                status_code=422,
                detail=f"Resume PDF must have {_MAX_RESUME_PAGES} pages or fewer.",
            )
        page_text = [(page.extract_text() or "").strip() for page in reader.pages]
        extracted = "\n\n".join(page_text)
        resume_text = "\n\n".join(part for part in extracted.split("\n\n") if part).strip()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Could not read this PDF.") from exc

    if len(resume_text) < 100:
        raise HTTPException(
            status_code=422,
            detail=(
                "This PDF does not contain enough selectable text. "
                "Export it as a text-based PDF instead of a scanned image."
            ),
        )

    extraction = extract_profile_facts(
        resume_text,
        page_count=len(reader.pages),
        pages_with_text=sum(bool(text) for text in page_text),
    )
    saved = create_resume_profile(
        _DEFAULT_USERNAME, filename, raw, resume_text, extraction
    )
    if not saved:
        raise HTTPException(status_code=500, detail="The resume could not be saved.")
    from profile import _snapshot
    return ResumeProfileResponse(**_public_snapshot(_snapshot(saved)))


@router.put("/resume/{profile_id}/activate", response_model=ResumeProfileResponse)
def review_and_activate_resume(profile_id: int, body: ResumeProfileReviewRequest):
    """Activate reviewed structured facts; raw PDF extraction stays immutable."""
    row = get_resume_profile(profile_id, _DEFAULT_USERNAME)
    if not row:
        raise HTTPException(status_code=404, detail="Resume profile not found.")
    if (row.get("readability") or {}).get("status") == "unreadable":
        raise HTTPException(status_code=422, detail="Unreadable PDF cannot be activated.")
    corrections = _review_corrections(row, body)
    saved = activate_resume_profile(
        profile_id, corrections, _clean_text(body.review_notes, 2_000), _DEFAULT_USERNAME
    )
    if not saved:
        raise HTTPException(status_code=500, detail="The reviewed profile could not be activated.")
    return ResumeProfileResponse(**_public_snapshot(saved))
