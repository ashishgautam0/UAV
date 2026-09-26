import hashlib
from io import BytesIO
from typing import Literal
import json
import re

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from pypdf import PdfReader

from ..models.schemas import (
    ApplicationPromptSettings,
    RenderedApplicationPrompt,
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
    get_application_prompt_settings,
    get_latest_profile_snapshot,
    get_profile,
    get_resume_profile,
    prune_obsolete_resume_profiles,
    save_application_prompt_settings,
    upsert_profile,
)
from resume_profile import extract_profile_facts, reviewed_experience_months, profile_text
from prep28 import (
    _encode_url_path,
    _ensure_pdf_bucket,
    _get_client as _storage_client,
    _PDF_BUCKET,
)

router = APIRouter()

_DEFAULT_USERNAME = "subidh"
_MAX_RESUME_BYTES = 10 * 1024 * 1024
_MAX_RESUME_PAGES = 30
_APPLICATION_PREFIX = "application-resumes"
_APPLICATION_ANSWER_LABELS = {
    "submission_authorization": "Submission authorization",
    "notice_period": "Notice period",
    "current_ctc": "Current compensation",
    "expected_ctc": "Expected compensation",
    "expected_start_date": "Expected start date",
    "current_location": "Current location",
    "relocation_preference": "Relocation preference",
}
_PROMPT_PLACEHOLDER = re.compile(r"{{([a-z_][a-z0-9_]*)}}")


def _application_path(source_sha256):
    if not re.fullmatch(r"[a-f0-9]{64}", source_sha256 or ""):
        raise HTTPException(status_code=404, detail="Resume not found.")
    return f"{_APPLICATION_PREFIX}/{_DEFAULT_USERNAME}/{source_sha256}.pdf"


def _stored_application_paths(bucket):
    """List current and legacy resume objects, bounded to two folder levels."""
    paths = []
    for item in bucket.list(_APPLICATION_PREFIX) or []:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        name = str(item["name"])
        direct = f"{_APPLICATION_PREFIX}/{name}"
        if name.lower().endswith(".pdf"):
            paths.append(direct)
            continue
        for child in bucket.list(direct) or []:
            if isinstance(child, dict) and str(child.get("name", "")).lower().endswith(".pdf"):
                paths.append(f"{direct}/{child['name']}")
    return paths


def _store_application_pdf(raw, source_sha256):
    """Store the candidate PDF without disturbing the current valid object."""
    db = _storage_client()
    _ensure_pdf_bucket(db)
    bucket = db.storage.from_(_PDF_BUCKET)
    current = _application_path(source_sha256)
    bucket.upload(current, raw, {
        "content-type": "application/pdf", "upsert": "true", "cache-control": "0",
    })
    return current


def _remove_obsolete_application_pdfs(source_sha256):
    bucket = _storage_client().storage.from_(_PDF_BUCKET)
    current = _application_path(source_sha256)
    obsolete = [path for path in _stored_application_paths(bucket) if path != current]
    if obsolete:
        bucket.remove(obsolete)
    return len(obsolete)


def _application_pdf_metadata():
    latest = get_latest_profile_snapshot(_DEFAULT_USERNAME)
    if not latest:
        return None
    path = _application_path(latest.get("source_sha256"))
    try:
        bucket = _storage_client().storage.from_(_PDF_BUCKET)
        filename = path.rsplit("/", 1)[-1]
        entries = bucket.list(path.rsplit("/", 1)[0]) or []
        entry = next(item for item in entries
                     if isinstance(item, dict) and item.get("name") == filename)
    except Exception:
        return None
    metadata = entry.get("metadata") or {}
    size = metadata.get("size") or metadata.get("contentLength") or entry.get("size")
    return {
        "filename": latest.get("source_filename") or "Resume.pdf",
        "sha256": latest.get("source_sha256"),
        "size": size,
        "version": latest.get("version"),
        "profile_status": latest.get("status"),
    }


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


@router.get("/application-settings", response_model=ApplicationPromptSettings)
def read_application_settings():
    """Load application answers from backend state for any browser/device."""
    return ApplicationPromptSettings(**get_application_prompt_settings(_DEFAULT_USERNAME))


@router.put("/application-settings", response_model=ApplicationPromptSettings)
def update_application_settings(body: ApplicationPromptSettings):
    payload = {
        key: _clean_text(value, 12_000 if key.endswith("template") else 500)
        for key, value in body.model_dump(exclude_unset=True).items()
    }
    saved = save_application_prompt_settings(_DEFAULT_USERNAME, payload)
    if saved is None:
        raise HTTPException(status_code=500, detail="Application prompt settings could not be saved.")
    return ApplicationPromptSettings(**saved)


def _render_application_prompt(template, settings, jobs, resume, page_url, resume_url):
    """Render one immutable browser-agent batch without browser-local state."""
    answer_lines = [
        f"- {_APPLICATION_ANSWER_LABELS[key]}: {settings.get(key)}"
        for key in _APPLICATION_ANSWER_LABELS
        if settings.get(key)
    ]
    batch = [{
        "job_id": job.get("id"),
        "title": job.get("title") or "",
        "company": job.get("company") or "",
        "location": job.get("location") or "",
        "source": job.get("source") or "",
        "url": job.get("url") or "",
        "screening_status": job.get("screening_status") or "pending",
        "screening_reason": job.get("screening_reason") or "",
    } for job in jobs]
    values = {
        "application_answers": "\n".join(answer_lines) or "- No application-form answers are saved.",
        "page_url": page_url,
        "resume_filename": (resume or {}).get("filename") or "Resume.pdf",
        "resume_url": resume_url,
        "resume_sha256": (resume or {}).get("sha256") or "unavailable",
        "batch_jobs": json.dumps(batch, ensure_ascii=False, indent=2, default=str),
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    unresolved = sorted(set(_PROMPT_PLACEHOLDER.findall(rendered)))
    envelope = (
        "AUTOMATION RULES (authoritative):\n"
        "- Start working through the fixed batch immediately; do not stop after only describing a plan.\n"
        "- Apply only when screening_status is pass. Treat pending, review, fail, missing URLs, "
        "or unclear mandatory eligibility as blocked and do not submit them.\n"
        "- Complete browser work autonomously where supported, but pause for any confirmation, "
        "login, CAPTCHA, sensitive-data approval, or missing truthful answer required by the platform.\n"
        "- If the original job listing definitively says it is no longer accepting applications "
        "or its page is permanently not found, return to Today Todo and remove only its matching "
        "job card (match job ID and URL; swipe left to Remove). Verify the card disappears, "
        "then continue the batch. Do not mark it Applied or delete the database record. "
        "For a temporary page error, login, CAPTCHA, or uncertain availability, leave its card "
        "in place and report the blocker.\n"
        "- Never invent an answer, bypass a control, pay a fee, or apply outside this batch. "
        "Do not send HR emails, cold DMs or follow-ups in this application task; use their separate Settings prompts.\n\n"
    )
    return envelope + rendered, unresolved


@router.get("/application-prompt", response_model=RenderedApplicationPrompt)
def read_rendered_application_prompt(request: Request, page_url: str):
    """Return one complete Codex prompt using current backend jobs and PDF."""
    page_url = _clean_text(page_url, 1_000)
    if not page_url.startswith(("https://", "http://localhost")):
        raise HTTPException(status_code=422, detail="Today Todo page URL is invalid.")

    from tracker import get_scraped_jobs

    settings = get_application_prompt_settings(_DEFAULT_USERNAME)
    frame = get_scraped_jobs()
    jobs = frame.to_dict("records") if hasattr(frame, "to_dict") else list(frame or [])
    resume = _application_pdf_metadata()
    resume_url = str(request.url_for("download_application_resume"))
    prompt, unresolved = _render_application_prompt(
        settings["prompt_template"], settings, jobs, resume, page_url, resume_url,
    )
    issues = []
    if not jobs:
        issues.append("No current Today Todo jobs are available.")
    if not resume:
        issues.append("No latest Settings PDF is available.")
    if not settings.get("submission_authorization"):
        issues.append("Submission authorization is blank in Settings.")
    if unresolved:
        issues.append("The saved template contains unresolved placeholders.")
    return RenderedApplicationPrompt(
        prompt=prompt,
        job_count=len(jobs),
        resume_available=bool(resume),
        ready=not issues,
        issues=issues,
        unresolved_placeholders=unresolved,
    )


def _public_snapshot(snapshot):
    if not snapshot:
        return None
    result = {key: value for key, value in snapshot.items() if key not in {"raw_text", "corrections"}}
    result["backend_text"] = profile_text(snapshot)
    return result


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
    digest = hashlib.sha256(raw).hexdigest()
    previous = get_latest_profile_snapshot(_DEFAULT_USERNAME)
    previous_digest = (previous or {}).get("source_sha256")
    try:
        _store_application_pdf(raw, digest)
        saved = create_resume_profile(
            _DEFAULT_USERNAME, filename, raw, resume_text, extraction
        )
    except Exception:
        # A failed database write must not leave the failed replacement active.
        if digest != previous_digest:
            try:
                _storage_client().storage.from_(_PDF_BUCKET).remove([_application_path(digest)])
            except Exception:
                pass
        raise
    if not saved:
        if digest != previous_digest:
            try:
                _storage_client().storage.from_(_PDF_BUCKET).remove([_application_path(digest)])
            except Exception:
                pass
        raise HTTPException(status_code=500, detail="The resume could not be saved.")
    _remove_obsolete_application_pdfs(digest)
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
    try:
        prune_obsolete_resume_profiles(saved["id"], _DEFAULT_USERNAME)
    except Exception as exc:
        # Activation is already committed. Preserve referenced rows and defer
        # unexpected cleanup failures rather than reporting a false failure.
        print(f"[profile] obsolete resume cleanup deferred: {exc}")
    return ResumeProfileResponse(**_public_snapshot(saved))


@router.get("/resume/application")
def application_resume_status():
    """Return the last Settings-uploaded PDF without browser-local state."""
    metadata = _application_pdf_metadata()
    return {"available": bool(metadata), **(metadata or {})}


@router.get("/resume/pdf")
def download_application_resume():
    """Redirect to a short-lived private Storage URL to avoid response limits."""
    latest = get_latest_profile_snapshot(_DEFAULT_USERNAME)
    if not latest or not _application_pdf_metadata():
        raise HTTPException(
            status_code=404,
            detail="Resume PDF unavailable. Upload it again from Settings.",
        )
    result = _storage_client().storage.from_(_PDF_BUCKET).create_signed_url(
        _application_path(latest.get("source_sha256")), 300
    )
    signed = result.get("signedURL") or result.get("signedUrl")
    if not signed:
        raise HTTPException(status_code=500, detail="Could not create the resume download link.")
    return RedirectResponse(_encode_url_path(signed), status_code=307, headers={
        "Cache-Control": "private, no-store",
        "Referrer-Policy": "no-referrer",
    })


def _render_outreach_prompt(template, resume, page_url, resume_url, kind="hr_email"):
    from outreach_prompts import GMAIL_HR_DELIVERY_RULES, LINKEDIN_CONNECTION_RULES
    values = {"page_url": page_url, "resume_filename": (resume or {}).get("filename") or "Resume.pdf",
              "resume_url": resume_url, "resume_sha256": (resume or {}).get("sha256") or "unavailable"}
    rendered = _PROMPT_PLACEHOLDER.sub(lambda match: values.get(match.group(1), match.group(0)), template)
    unresolved = sorted(set(_PROMPT_PLACEHOLDER.findall(rendered)))
    rules = ("TASK RULES: Execute only this selected outreach workflow. Do not submit applications or run other outreach queues. "
             "Use verified facts and recipients only. Check conversation/Sent history to avoid duplicates. "
             "Obtain explicit confirmation immediately before sending. Never record success without observed send evidence. "
             "Report missing tools, login or assets rather than guessing or bypassing controls.\n\n")
    delivery = GMAIL_HR_DELIVERY_RULES if kind in {"hr_email", "followup"} else LINKEDIN_CONNECTION_RULES
    return rules + delivery + rendered, unresolved


@router.get("/outreach-prompt", response_model=RenderedApplicationPrompt)
def read_outreach_prompt(request: Request, page_url: str,
                         kind: Literal["hr_email", "followup", "cold_dm"]):
    page_url = _clean_text(page_url, 1_000)
    if not page_url.startswith(("https://", "http://localhost")):
        raise HTTPException(status_code=422, detail="App page URL is invalid.")
    settings = get_application_prompt_settings(_DEFAULT_USERNAME)
    resume = _application_pdf_metadata()
    prompt, unresolved = _render_outreach_prompt(settings[kind + "_template"], resume, page_url,
                                                 str(request.url_for("download_application_resume")), kind)
    issues = []
    if not resume:
        issues.append("No latest Settings PDF is available.")
    if unresolved:
        issues.append("The saved template contains unresolved placeholders.")
    return RenderedApplicationPrompt(prompt=prompt, job_count=0, resume_available=bool(resume),
                                     ready=not issues, issues=issues, unresolved_placeholders=unresolved)
