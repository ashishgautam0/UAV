import hashlib
from io import BytesIO
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
_PROMPT_PLACEHOLDER = re.compile(r"{{([a-z_]+)}}")


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
        key: _clean_text(value, 12_000 if key == "prompt_template" else 500)
        for key, value in body.model_dump().items()
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
        "- Never invent an answer, bypass a control, pay a fee, or apply outside this batch. "
        "Outreach is limited to the confirmed HR-email and due follow-up steps below.\n\n"
    )
    hr_step = (
        "\n\nHR EMAIL — AFTER TRACKER LOGGING (part of this task):\n"
        "1. After processing applications, open Dashboard using the app navigation. Use only "
        "its 'Email Company HR' todo section to decide which companies need email. This "
        "dashboard queue is separate from the fixed Today Todo application batch and can include "
        "previously tracked jobs. Do not scan company details or every Tracker record to find "
        "email work. Snapshot the pending dashboard todos once; do not chase newly appearing "
        "todos indefinitely. If the section fails to load, report a queue error; if empty, "
        "report no pending HR emails.\n"
        "For each queued todo, click that dashboard card to open its corresponding Tracker job "
        "detail. Confirm the company/role and posting URL match the todo; never guess a Tracker ID "
        "from the scraped-job ID. If the link or matching record is missing, report that todo "
        "blocked and continue. Do not generate or send HR email before tracking.\n"
        "2. In 'Email to Company HR', inspect completion status. If already completed, skip. "
        "If the stored HR draft or live mini demo is not ready, record 'HR email pending assets' "
        "and continue; do not invent a demo or wait indefinitely. The Claude routine remains "
        "responsible for generating the stored draft after tracking.\n"
        "3. To: use the draft's recipient only after verifying it against the company's hiring "
        "contacts or official careers website. Unknown, guessed or conflicting addresses require "
        "user resolution; never infer careers@ or send to multiple contacts automatically.\n"
        "4. Subject: copy the specific role/company subject from the stored draft into the "
        "mail client's Subject field. Body: use only the email body, without To/Subject headers; "
        "keep it short, professional, 70–110 words and grounded in verified resume facts. "
        "Include the exact live mini-demo link for this job and mention the attached resume.\n"
        "5. Attachment: use 'Resume to attach' on the Tracker detail page to download the latest "
        "Settings PDF. Verify its current filename/hash against Settings; if it changed since "
        "this batch or disagrees with the draft's facts, stop this email for review/regeneration. "
        "Upload the actual PDF as a file attachment, not a link in the body, and verify that "
        "the mail composer shows the correct attachment fully uploaded.\n"
        "6. Use the user's available authenticated email browser or supported connected mail "
        "tool. If neither is available, report 'HR email blocked: mail access required'. Never "
        "request passwords in chat or assume a mail integration exists. Follow all required "
        "approvals before transmitting personal data.\n"
        "7. Before sending, check Sent mail for this recipient and job to avoid duplicates. "
        "Show the sender account, To, Subject, full body and attachment filename and obtain "
        "explicit confirmation immediately before Send. Do not treat saved application "
        "authorization as email-send confirmation.\n"
        "8. Only after observing a sent confirmation or matching Sent item, click 'Mark emailed' "
        "on the same Tracker record and verify completion persists. Return to Dashboard and "
        "verify that todo is no longer pending, then open the next snapshotted dashboard todo. "
        "If logging fails, retry "
        "logging only. If sending times out or its outcome is uncertain, check Sent first; "
        "never blindly resend or mark completed. Do not reopen completed todos.\n"
        "Include a separate per-job HR result in the final report: sent and recorded, already "
        "sent, pending assets, awaiting confirmation, or blocked with reason. Never report a "
        "draft or an open composer as sent.\n"
    )
    followup_step = (
        "\n\nFOLLOW-UPS — DASHBOARD QUEUE (part of this task):\n"
        "1. After the HR-email step, open Dashboard's 'Follow-ups Due' section. Snapshot that "
        "queue once, including previously tracked jobs outside the application batch. Click "
        "each dashboard follow-up card to open its linked Tracker detail; do not scan all "
        "companies or guess IDs. Verify the company, role and posting URL. Report broken links "
        "or load errors as blocked, not as an empty queue.\n"
        "2. Recheck the saved follow-up date in Asia/Kolkata and recorded history. Process only "
        "due or overdue follow-ups; skip future dates, terminal records, or already-recorded "
        "follow-up numbers. Never change a date to make a job due. If an initial HR email was "
        "just sent for this job during this run, defer the follow-up to avoid two messages "
        "together; leave its schedule unchanged and report the deferral.\n"
        "3. Use the current 'Follow-up draft' and its displayed follow-up number. If queued, "
        "missing, stale or inconsistent with history, report pending draft and continue. "
        "Do not substitute the initial HR email or invent previous contact, replies or facts. "
        "Keep the body brief, polite and professional.\n"
        "4. Use the verified recipient and existing conversation/channel from previous outreach. "
        "For email, use To, the existing thread Subject (or a short role-specific subject), "
        "and the follow-up body. Include the correct live mini-demo link and actual latest "
        "Settings PDF attachment, applying the same resume, upload and recipient checks as "
        "the HR step. Do not claim an attachment exists in a channel that cannot attach it. "
        "If contact, channel, demo, resume or authenticated mail access is unavailable, report "
        "blocked rather than guessing or switching recipients.\n"
        "5. Inspect Sent mail or conversation history for this follow-up before sending. "
        "Show sender, recipient, subject, full message and attachment, and obtain explicit "
        "confirmation immediately before Send. Respect required data-sharing approvals. "
        "After an uncertain send, check the conversation; never blindly resend.\n"
        "6. Only after verified sending, fill 'Sent follow-up message' with the exact sent text, "
        "select 'Sent via', and click 'Record sent follow-up' on the same Tracker detail. "
        "This records history and advances the existing cadence; do not also change status "
        "to 'Follow-up Sent' or click 'Mark emailed', which belongs to the separate initial HR todo. "
        "Verify the new history row, number, channel, message and timestamp, then return to "
        "Dashboard and check the updated date/queue. If logging is uncertain, inspect history "
        "before any retry; never resend or record twice. A still-overdue next date does not "
        "authorize another follow-up in this run. Process at most one follow-up per record.\n"
        "Report each follow-up separately: sent and recorded, already sent, pending draft, "
        "deferred, awaiting confirmation, or blocked with reason. Never fabricate history.\n"
    )
    return envelope + rendered + hr_step + followup_step, unresolved


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
