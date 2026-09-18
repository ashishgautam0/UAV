"""Safe file boundary for the ChatGPT Work + Supabase-connector routine.

The Supabase plugin owns database authentication.  This module never accepts a
Supabase URL or key.  It consumes bounded JSON exported by connector reads,
runs the repository's existing Python filters and prompt builders, and emits
bounded JSON mutation plans.  The scheduled ChatGPT session applies those
mutations through the authenticated connector.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
MAX_EXISTING_URLS = 20_000
MAX_SCREEN = 100
MAX_RESCORE = 100
MAX_OUTREACH = 10
MAX_REQUESTS = 20
MAX_DUE_APPLICATIONS = 100
MAX_HISTORY = 500
MAX_ACTIVE_REQUESTS = 200
MAX_COVER_LETTERS = 20
COVER_LETTER_RULES_VERSION = "grounded-cover-letter-v1"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+-]{7,127}$")


def _jd_hash(text):
    return hashlib.sha256((text or "").strip().encode("utf-8")).hexdigest()


def _read(path):
    with open(path, encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    return value


def _write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _rows(value, name, maximum):
    rows = value.get(name, [])
    if not isinstance(rows, list):
        raise ValueError(f"{name} must be an array")
    if len(rows) > maximum:
        raise ValueError(f"{name} exceeds the {maximum}-row safety bound")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"every {name} item must be an object")
    return rows


def _run_id(value):
    run_id = value.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must be an 8-128 character stable identifier")
    return run_id


def _id(row, name):
    value = row.get(name)
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer (booleans are invalid)")
    return value


def _text(row, name, maximum, *, required=True):
    value = row.get(name)
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{name} must not be empty")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} characters")
    if any((unicodedata.category(ch) == "Cc" and ch not in "\n\r\t")
           or unicodedata.category(ch) == "Cs" for ch in value):
        raise ValueError(f"{name} contains a disallowed control character")
    return value


def _char_limit(value, name):
    if type(value) is not int or not 1 <= value <= 20_000:
        raise ValueError(f"{name} must be an integer between 1 and 20000")
    return value


def _unique_ids(rows, name, key):
    seen = set()
    for row in rows:
        value = _id(row, key)
        if value in seen:
            raise ValueError(f"duplicate {key} {value} in {name}")
        seen.add(value)
    return seen


def _allowed_id_set(allowed, name):
    values = allowed.get(name)
    if not isinstance(values, list):
        raise ValueError(f"validated actions are missing allowed_ids.{name}")
    rows = [{"id": value} for value in values]
    return _unique_ids(rows, f"allowed_ids.{name}", "id")


def _validate_cover_grounding(content, profile, job_description):
    """Reject high-confidence invented claims; the session remains responsible
    for semantic grounding that a deterministic checker cannot prove."""
    sources = f"{profile}\n{job_description}"
    source_numbers = set(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?%?(?!\w)", sources))
    draft_numbers = set(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?%?(?!\w)", content))
    unsupported_numbers = sorted(draft_numbers - source_numbers)
    if unsupported_numbers:
        raise ValueError(
            "cover letter contains numeric claims absent from its resume/JD evidence: "
            + ", ".join(unsupported_numbers)
        )

    from resume_profile import SKILL_ALIASES, phrase_present
    claim_markers = re.compile(
        r"\b(?:i (?:have|built|used|developed|implemented|led|hold|earned)|"
        r"my (?:experience|expertise|skills?|certification|degree)|proficient in)\b",
        re.IGNORECASE,
    )
    for sentence in re.split(r"(?<=[.!?])\s+", content):
        if not claim_markers.search(sentence):
            continue
        for skill, aliases in SKILL_ALIASES.items():
            if any(phrase_present(sentence, alias) for alias in aliases) and not any(
                phrase_present(profile, alias) for alias in aliases
            ):
                raise ValueError(
                    f"cover letter claims {skill!r} without active-profile evidence"
                )


def profile_text(row):
    """Render only a reviewed active PDF snapshot; never use legacy defaults."""
    row = row or {}
    if row.get("status") != "active" or row.get("source_kind") != "pdf":
        return ""
    from resume_profile import profile_text as render_profile
    resume = render_profile(row).strip()
    return resume if len((row.get("raw_text") or "").strip()) >= 100 else ""


def _next_alert(subject):
    match = re.search(r"#(\d+)", subject or "")
    return int(match.group(1)) + 1 if match else 1


def scrape_plan(context):
    """Run the existing scraper/filter pipeline without database credentials."""
    run_id = _run_id(context)
    urls = context.get("existing_job_urls", [])
    if not isinstance(urls, list) or len(urls) > MAX_EXISTING_URLS:
        raise ValueError(f"existing_job_urls must contain at most {MAX_EXISTING_URLS} values")
    existing = {url for url in urls if isinstance(url, str) and url}
    existing_rows = context.get("existing_jobs", [])
    if not isinstance(existing_rows, list) or len(existing_rows) > MAX_EXISTING_URLS:
        raise ValueError(f"existing_jobs must contain at most {MAX_EXISTING_URLS} values")
    existing_hashes = {}
    for row in existing_rows:
        if not isinstance(row, dict) or not isinstance(row.get("url"), str):
            raise ValueError("every existing_jobs item needs a text url")
        existing_hashes[row["url"]] = row.get("jd_hash")

    from digest import build_email_content
    from hourly import _experience_ok, _matches_desired_title, _resume_fit_filter
    from scraper import check_apply_type, run_all_scrapers

    profile_snapshot = context.get("active_profile") or {}
    resume = profile_text(profile_snapshot)
    jobs, sources_status, sources_errors = run_all_scrapers()
    new_jobs = []
    changed_jobs = 0
    for job in jobs:
        url = job.get("url", "")
        digest = _jd_hash(job.get("description"))
        if url in existing_hashes:
            if existing_hashes[url] == digest:
                continue
            changed_jobs += 1
        elif url in existing:
            continue
        new_jobs.append(job)
    counts = {"found": len(jobs), "after_dedup": len(new_jobs), "changed_jd": changed_jobs}
    new_jobs = [job for job in new_jobs if _matches_desired_title(job.get("title", ""))]
    counts["after_title"] = len(new_jobs)
    new_jobs = [job for job in new_jobs if _experience_ok(job.get("description", ""), profile_snapshot)]
    counts["after_experience"] = len(new_jobs)
    new_jobs, resume_note = _resume_fit_filter(new_jobs, resume, profile_snapshot)
    counts["after_resume_net"] = len(new_jobs)

    try:
        from jd_analyzer import full_analyze, quick_ats
        for job in new_jobs[:15]:
            try:
                result = full_analyze(job.get("title", ""), job.get("description", ""), profile_snapshot, job.get("location", ""))
                job["ats_score"] = quick_ats(job.get("description", ""), profile_snapshot)
                job["skill_match"] = result.get("skills", {}).get("match_percentage")
                job["noc_verdict"] = (result.get("noc") or {}).get("confidence", "")
                job["analysis_details"] = result
                job["analysis_version"] = result.get("analysis_version")
                job["profile_version"] = profile_snapshot.get("version")
            except Exception:
                pass
    except ImportError:
        pass

    delay = float(os.environ.get("APPLY_CHECK_DELAY_SECONDS", "1"))
    for job in new_jobs:
        job["verdict"] = check_apply_type(job.get("url", ""))
        if delay:
            time.sleep(delay)

    allowed = ("title", "company", "location", "source", "url", "description",
               "score", "noc_verdict", "skill_match", "verdict", "ats_score",
               "analysis_details", "analysis_version", "profile_version")
    db_jobs = []
    for job in new_jobs:
        row = {key: job.get(key) for key in allowed}
        row["score"] = row.get("score") or 0
        row["jd_hash"] = _jd_hash(row.get("description"))
        db_jobs.append(row)
    alert = _next_alert(context.get("last_email_subject", ""))
    email_log = None
    notification = None
    if new_jobs:
        for job in new_jobs:
            job["filtered"] = True
        email_log = {
            "subject": f"Job Alert #{alert}",
            "markdown_content": build_email_content(new_jobs, sources_status, sources_errors),
            "html_content": "",
            "jobs_count": len(new_jobs),
            "sources_summary": sources_status,
            "email_sent": False,
        }
        notification = {
            "title": f"Job Alert #{alert}", "body": f"{len(new_jobs)} new jobs found",
            "type": "job_alert", "metadata": {"jobs_count": len(new_jobs), "alert_number": alert, "sources": sources_status},
        }
    health = None
    if sources_status.get("LinkedIn AI/ML", 0) == 0 and "LinkedIn AI/ML" not in sources_errors:
        health = {"title": "Scraper Health Check Failed", "body": "LinkedIn AI/ML scraper returned 0 results. Possible scraper failure — check logs.", "type": "health_check", "metadata": {"source": "LinkedIn AI/ML", "timestamp": datetime.now(timezone.utc).isoformat()}}
    return {"schema_version": SCHEMA_VERSION, "run_id": run_id, "kind": "scrape", "jobs": db_jobs,
            "email_log": email_log, "notification": notification, "health_notification": health,
            "stats": {**counts, "resume_net": resume_note, "sources": sources_status,
                      "source_errors": sources_errors}}


def prepare_items(context):
    """Prepare bounded screening/drafting work and idempotent follow-up inserts."""
    run_id = _run_id(context)
    completeness = context.get("completeness")
    if not isinstance(completeness, dict):
        raise ValueError("completeness must be an object")
    for name in ("follow_up_history", "active_followup_requests"):
        if completeness.get(name) is not True:
            raise ValueError(f"{name} export is not explicitly complete")
    profile_snapshot = context.get("active_profile") or {}
    profile = profile_text(profile_snapshot)
    rescore = _rows(context, "rescore_jobs", MAX_RESCORE)
    screen = _rows(context, "screen_jobs", MAX_SCREEN)
    outreach = _rows(context, "outreach_jobs", MAX_OUTREACH)
    pending = _rows(context, "pending_requests", MAX_REQUESTS)
    due = _rows(context, "due_applications", MAX_DUE_APPLICATIONS)
    history = _rows(context, "follow_up_history", MAX_HISTORY)
    active = _rows(context, "active_followup_requests", MAX_ACTIVE_REQUESTS)
    cover_candidates = _rows(context, "cover_letter_jobs", MAX_COVER_LETTERS)
    _unique_ids(rescore, "rescore_jobs", "id")
    _unique_ids(screen, "screen_jobs", "id")
    _unique_ids(outreach, "outreach_jobs", "id")
    _unique_ids(pending, "pending_requests", "id")
    _unique_ids(due, "due_applications", "id")
    _unique_ids(cover_candidates, "cover_letter_jobs", "id")

    rescored_jobs = []
    if rescore and not profile:
        raise ValueError("rescore_jobs require one active reviewed PDF profile")
    if rescore:
        from jd_analyzer import full_analyze, quick_ats
        profile_version = _id(profile_snapshot, "version")
        for row in rescore:
            description = _text(row, "description", 100_000, required=False)
            jd_hash = _jd_hash(description)
            if row.get("jd_hash") != jd_hash:
                raise ValueError(f"rescore job {row['id']} JD hash does not match its description")
            analysis = full_analyze(
                row.get("title") or "", description, profile_snapshot,
                row.get("location") or "",
            )
            rescored_jobs.append({
                "job_id": row["id"], "jd_hash": jd_hash,
                "jd_version": _id(row, "jd_version"),
                "profile_version": profile_version,
                "ats_score": quick_ats(description, profile_snapshot),
                "skill_match": (analysis.get("skills") or {}).get("match_percentage"),
                "noc_verdict": (analysis.get("noc") or {}).get("confidence") or "",
                "analysis_version": analysis.get("analysis_version"),
                "analysis_details": analysis,
            })

    existing = set()
    for request in active:
        params = request.get("params") or {}
        if request.get("status") in ("pending", "ready") and params.get("_application_id"):
            existing.add((params["_application_id"], params.get("follow_up_number", 1)))
    by_app = {}
    for row in history:
        if row.get("entity_type") == "application":
            by_app.setdefault(row.get("entity_id"), []).append(row)
    followups = []
    for app in due:
        prior = sorted(by_app.get(app.get("id"), []), key=lambda x: x.get("sent_at") or "")
        number = len(prior) + 1
        if number > 3 or (app.get("id"), number) in existing:
            continue
        try:
            applied = datetime.strptime(str(app.get("date_applied", ""))[:10], "%Y-%m-%d").date()
            days = max((date.today() - applied).days, 1)
        except (TypeError, ValueError):
            days = 7
        followups.append({"message_type": "follow-up", "params": {
            "company_name": app.get("company", ""), "role_title": app.get("role", ""),
            "days_since_applied": days, "original_platform": app.get("platform") or "LinkedIn",
            "follow_up_number": number,
            "previous_messages": [row.get("message_content", "") for row in prior[-3:] if row.get("message_content")],
            "_application_id": app.get("id"),
        }})

    from message_generator import PROMPT_BUILDERS
    requests = []
    for row in pending:
        params = {key: value for key, value in (row.get("params") or {}).items() if not key.startswith("_")}
        builder = PROMPT_BUILDERS.get(row.get("message_type"))
        if not builder:
            requests.append({"request_id": row.get("id"), "error": f"unknown message_type {row.get('message_type')!r}"})
            continue
        import inspect
        if "profile_text" in inspect.signature(builder).parameters:
            params["profile_text"] = profile
        try:
            requests.append({"request_id": row.get("id"), "message_type": row.get("message_type"), **builder(**params)})
        except TypeError as exc:
            requests.append({"request_id": row.get("id"), "error": f"params do not match builder: {exc}"})
    outreach_items = [{**row, "char_limit": 600} for row in outreach]
    try:
        threshold = int(context.get("cover_letter_threshold", 90))
    except (TypeError, ValueError):
        raise ValueError("cover_letter_threshold must be an integer")
    if not 0 <= threshold <= 100:
        raise ValueError("cover_letter_threshold must be between 0 and 100")
    from message_generator import build_cover_letter_prompt
    cover_letters = []
    if cover_candidates:
        profile_id = _id(profile_snapshot, "id")
        profile_version = _id(profile_snapshot, "version")
    for row in cover_candidates:
        details = row.get("analysis_details") or {}
        eligibility = details.get("mandatory_eligibility") or {}
        score = row.get("ats_score")
        if row.get("analysis_stale") is not False or row.get("screen_decision") != "pass":
            continue
        if type(score) is not int or not 0 <= score <= 100:
            raise ValueError("cover letter match score must be an integer from 0 to 100")
        if score < threshold or eligibility.get("overall") != "passed":
            continue
        if row.get("profile_version") != profile_version or not profile:
            continue
        jd_version = row.get("jd_version")
        if type(jd_version) is not int or jd_version <= 0:
            raise ValueError("cover letter jd_version must be a positive integer")
        analysis_version = _text(row, "analysis_version", 200)
        if details.get("analysis_version") != analysis_version:
            raise ValueError("cover letter analysis version does not match its analysis details")
        detail_score = (details.get("resume_jd_match") or {}).get("score")
        if type(detail_score) is not int or detail_score != score:
            raise ValueError("cover letter score does not match its analysis details")
        jd = _text(row, "description", 100_000)
        jd_hash = _jd_hash(jd)
        if row.get("jd_hash") != jd_hash:
            continue
        spec = build_cover_letter_prompt(row.get("company") or "Unknown", row.get("title") or "Role", jd, profile_text=profile)
        cover_letters.append({
            "job_id": row["id"], "resume_profile_id": profile_id,
            "resume_version": profile_version,
            "jd_version": jd_version, "jd_hash": jd_hash,
            "match_score": score, "analysis_version": analysis_version,
            "rules_version": COVER_LETTER_RULES_VERSION,
            "grounding_profile": profile, "job_description": jd, **spec,
        })
    return {"schema_version": SCHEMA_VERSION, "run_id": run_id, "kind": "items", "profile": profile,
            "rescored_jobs": rescored_jobs, "screen_jobs": screen,
            "outreach_jobs": outreach_items, "requests": requests,
            "cover_letters": cover_letters, "cover_letter_threshold": threshold,
            "followup_requests": followups}


def validate_actions(prepared, actions):
    """Validate responses against the exact prepared batch before writes."""
    run_id = _run_id(prepared)
    if prepared.get("kind") != "items":
        raise ValueError("prepared context must have kind=items")
    if _run_id(actions) != run_id:
        raise ValueError("actions run_id does not match prepared context")
    screens = _rows(actions, "screens", MAX_SCREEN)
    outreach = _rows(actions, "outreach_drafts", MAX_OUTREACH)
    results = _rows(actions, "request_results", MAX_REQUESTS)
    letters = _rows(actions, "cover_letter_drafts", MAX_COVER_LETTERS)
    screen_ids = _unique_ids(screens, "screens", "job_id")
    outreach_ids = _unique_ids(outreach, "outreach_drafts", "job_id")
    request_ids = _unique_ids(results, "request_results", "request_id")
    letter_ids = _unique_ids(letters, "cover_letter_drafts", "job_id")
    prepared_screen = _rows(prepared, "screen_jobs", MAX_SCREEN)
    _unique_ids(prepared_screen, "prepared screen_jobs", "id")
    allowed_screen = {_id(row, "id") for row in prepared_screen}
    allowed_outreach_rows = _rows(prepared, "outreach_jobs", MAX_OUTREACH)
    _unique_ids(allowed_outreach_rows, "prepared outreach_jobs", "id")
    allowed_outreach = {_id(row, "id"): row for row in allowed_outreach_rows}
    allowed_request_rows = _rows(prepared, "requests", MAX_REQUESTS)
    _unique_ids(allowed_request_rows, "prepared requests", "request_id")
    allowed_requests = {_id(row, "request_id"): row for row in allowed_request_rows}
    allowed_letter_rows = _rows(prepared, "cover_letters", MAX_COVER_LETTERS)
    _unique_ids(allowed_letter_rows, "prepared cover_letters", "job_id")
    allowed_letters = {_id(row, "job_id"): row for row in allowed_letter_rows}
    if not screen_ids <= allowed_screen:
        raise ValueError("screen job_id is outside the exported batch")
    if not outreach_ids <= set(allowed_outreach):
        raise ValueError("outreach job_id is outside the exported batch")
    if not request_ids <= set(allowed_requests):
        raise ValueError("request_id is outside the exported batch")
    if not letter_ids <= set(allowed_letters):
        raise ValueError("cover-letter job_id is outside the exported batch")

    from message_generator import enforce_char_limit
    clean_screens = []
    for row in screens:
        if row.get("decision") not in ("pass", "fail", "review"):
            raise ValueError("each screen needs integer job_id and pass/fail/review decision")
        prepared_row = next(item for item in prepared_screen if item["id"] == row["job_id"])
        clean_screens.append({"job_id": row["job_id"], "decision": row["decision"],
                              "profile_version": prepared_row.get("profile_version"),
                              "reason": _text(row, "reason", 2_000)})
    clean_outreach = []
    for row in outreach:
        if "message_type" in row and row["message_type"] != "cold_dm":
            raise ValueError("outreach message_type must be cold_dm")
        content = _text(row, "content", 20_000)
        outreach_limit = _char_limit(
            allowed_outreach[row["job_id"]].get("char_limit"),
            f"outreach job {row['job_id']} char_limit",
        )
        if outreach_limit != 600:
            raise ValueError("outreach char_limit must match the cold DM builder limit of 600")
        content = enforce_char_limit(content, outreach_limit).strip()
        if not content:
            raise ValueError("outreach content became empty after limit enforcement")
        clean_outreach.append({"job_id": row["job_id"], "content": content,
                               "profile_version": allowed_outreach[row["job_id"]].get("profile_version")})
    clean_results = []
    for row in results:
        if row.get("status") not in ("ready", "failed"):
            raise ValueError("each request result needs integer request_id and ready/failed status")
        field = "content" if row["status"] == "ready" else "error"
        content = _text(row, field, 20_000)
        if row["status"] == "ready":
            spec = allowed_requests[row["request_id"]]
            if spec.get("error"):
                raise ValueError(f"request {row['request_id']} cannot be fulfilled because its prompt failed")
            request_limit = _char_limit(
                spec.get("char_limit"), f"request {row['request_id']} char_limit"
            )
            content = enforce_char_limit(content, request_limit).strip()
            if not content:
                raise ValueError(f"request {row['request_id']} became empty after limit enforcement")
            clean_results.append({"request_id": row["request_id"], "status": "ready", "content": content})
        else:
            clean_results.append({"request_id": row["request_id"], "status": "failed", "error": content})
    clean_letters = []
    for row in letters:
        spec = allowed_letters[row["job_id"]]
        content = enforce_char_limit(_text(row, "content", 20_000), _char_limit(spec.get("char_limit"), "cover letter char_limit")).strip()
        if not content:
            raise ValueError("cover letter became empty after limit enforcement")
        _validate_cover_grounding(
            content,
            _text(spec, "grounding_profile", 100_000),
            _text(spec, "job_description", 100_000),
        )
        clean_letters.append({key: spec[key] for key in (
            "job_id", "resume_profile_id", "resume_version", "jd_version", "jd_hash",
            "match_score", "analysis_version", "rules_version"
        )} | {"content": content})
    notification = actions.get("notification")
    if not isinstance(notification, dict):
        raise ValueError("a final notification object is required")
    clean_notification = {
        "title": _text(notification, "title", 200),
        "body": _text(notification, "body", 2_000),
        "type": "run_summary",
        "metadata": notification.get("metadata") if isinstance(notification.get("metadata"), dict) else {},
    }
    return {"schema_version": SCHEMA_VERSION, "run_id": run_id, "kind": "actions",
            "screens": clean_screens, "outreach_drafts": clean_outreach,
            "request_results": clean_results, "cover_letter_drafts": clean_letters,
            "notification": clean_notification,
            "allowed_ids": {"screen": sorted(allowed_screen),
                            "outreach": sorted(allowed_outreach),
                            "requests": sorted(allowed_requests),
                            "cover_letters": sorted(allowed_letters)}}


def _json_sql(value):
    """Return an injection-safe jsonb expression (payload is base64, never SQL text)."""
    encoded = base64.b64encode(json.dumps(value, ensure_ascii=False).encode("utf-8")).decode("ascii")
    return f"convert_from(decode('{encoded}', 'base64'), 'UTF8')::jsonb"


def _notification_sql(row, run_id, stage, notification_type):
    if not row:
        return ""
    metadata = dict(row.get("metadata") or {})
    metadata.update({"run_id": run_id, "stage": stage})
    payload = _json_sql({"title": row["title"], "body": row["body"],
                         "type": notification_type, "metadata": metadata})
    return f"""
WITH p AS (SELECT {payload} AS j)
INSERT INTO public.notifications (title, body, type, metadata)
SELECT j->>'title', j->>'body', coalesce(j->>'type', 'run_summary'), coalesce(j->'metadata', '{{}}'::jsonb)
FROM p
WHERE NOT EXISTS (
  SELECT 1 FROM public.notifications n
  WHERE n.type = p.j->>'type'
    AND n.metadata->>'run_id' = p.j->'metadata'->>'run_id'
    AND n.metadata->>'stage' = p.j->'metadata'->>'stage'
);"""


def render_sql(plan):
    """Render an allowlisted mutation plan as one transaction.

    Values travel as base64-encoded JSON and are decoded by PostgreSQL.  No
    model-generated string is interpolated as SQL syntax or an identifier.
    """
    kind = plan.get("kind")
    run_id = _run_id(plan)
    statements = ["BEGIN;"]
    if kind == "scrape":
        jobs = _rows(plan, "jobs", 500)
        seen_urls = set()
        for row in jobs:
            url = _text(row, "url", 10_000)
            if url in seen_urls:
                raise ValueError(f"duplicate job url {url!r} in scrape plan")
            seen_urls.add(url)
            description = _text(row, "description", 100_000, required=False)
            if row.get("jd_hash") != _jd_hash(description):
                raise ValueError(f"scrape job {url!r} JD hash does not match its description")
        if jobs:
            payload = _json_sql(jobs)
            statements.append(f"""
WITH p AS (SELECT jsonb_array_elements({payload}) AS j),
changed AS MATERIALIZED (
  SELECT s.id FROM public.scraped_jobs s JOIN p ON s.url = p.j->>'url'
  WHERE s.jd_hash IS DISTINCT FROM p.j->>'jd_hash'
), upserted AS (
INSERT INTO public.scraped_jobs
  (title, company, location, source, url, description, score, noc_verdict, skill_match, verdict,
   ats_score, profile_version, analysis_version, analysis_details, analysis_stale, analyzed_at,
   jd_hash, jd_version)
SELECT j->>'title', j->>'company', j->>'location', j->>'source', j->>'url',
       j->>'description', coalesce((j->>'score')::integer, 0), coalesce(j->>'noc_verdict', ''),
       (j->>'skill_match')::integer, coalesce(j->>'verdict', ''),
       (j->>'ats_score')::integer, (j->>'profile_version')::integer,
       j->>'analysis_version', coalesce(j->'analysis_details', '{{}}'::jsonb),
       (j->>'profile_version') IS NULL, CASE WHEN j->>'analysis_version' IS NULL THEN NULL ELSE now() END,
       j->>'jd_hash', 1
FROM p WHERE nullif(j->>'url', '') IS NOT NULL
ON CONFLICT (url) DO UPDATE SET
  title = excluded.title, company = excluded.company, location = excluded.location,
  source = excluded.source, description = excluded.description,
  jd_version = CASE WHEN scraped_jobs.jd_hash IS DISTINCT FROM excluded.jd_hash
                    THEN scraped_jobs.jd_version + 1 ELSE scraped_jobs.jd_version END,
  jd_hash = excluded.jd_hash,
  ats_score = excluded.ats_score, skill_match = excluded.skill_match,
  noc_verdict = excluded.noc_verdict, profile_version = excluded.profile_version,
  analysis_version = excluded.analysis_version,
  analysis_details = excluded.analysis_details,
  analysis_stale = excluded.analysis_stale,
  analyzed_at = excluded.analyzed_at
  RETURNING id
)
UPDATE public.cover_letter_drafts d SET is_outdated = true
FROM changed WHERE d.scraped_job_id = changed.id AND d.is_outdated = false;""")
        email = plan.get("email_log")
        if email:
            payload = _json_sql(email)
            statements.append(f"""
WITH p AS (SELECT {payload} AS j)
INSERT INTO public.email_logs
  (subject, markdown_content, html_content, jobs_count, sources_summary, email_sent)
SELECT j->>'subject', coalesce(j->>'markdown_content', ''), coalesce(j->>'html_content', ''),
       coalesce((j->>'jobs_count')::integer, 0), coalesce(j->'sources_summary', '{{}}'::jsonb), false
FROM p WHERE NOT EXISTS (SELECT 1 FROM public.email_logs e WHERE e.subject = p.j->>'subject');""")
        statements.append(_notification_sql(plan.get("notification"), run_id, "job_alert", "job_alert"))
        statements.append(_notification_sql(plan.get("health_notification"), run_id, "health_check", "health_check"))
    elif kind == "items":
        rescores = _rows(plan, "rescored_jobs", MAX_RESCORE)
        _unique_ids(rescores, "rescored_jobs", "job_id")
        if rescores:
            payload = _json_sql(rescores)
            statements.append(f"""
WITH p AS (SELECT jsonb_array_elements({payload}) AS j)
UPDATE public.scraped_jobs s
SET ats_score = (p.j->>'ats_score')::integer,
    skill_match = (p.j->>'skill_match')::integer,
    noc_verdict = coalesce(p.j->>'noc_verdict', ''),
    profile_version = (p.j->>'profile_version')::integer,
    analysis_version = p.j->>'analysis_version',
    analysis_details = coalesce(p.j->'analysis_details', '{{}}'::jsonb),
    analysis_stale = false,
    analyzed_at = now()
FROM p
WHERE s.id = (p.j->>'job_id')::bigint
  AND s.analysis_stale = true
  AND s.jd_version = (p.j->>'jd_version')::integer
  AND s.jd_hash = p.j->>'jd_hash';""")
        rows = _rows(plan, "followup_requests", MAX_DUE_APPLICATIONS)
        if rows:
            payload = _json_sql(rows)
            statements.append(f"""
WITH p AS (SELECT jsonb_array_elements({payload}) AS j)
INSERT INTO public.message_requests (message_type, params, status)
SELECT 'follow-up', j->'params', 'pending' FROM p
WHERE NOT EXISTS (
  SELECT 1 FROM public.message_requests r
  WHERE r.message_type = 'follow-up' AND r.status IN ('pending', 'ready')
    AND r.params->>'_application_id' = p.j->'params'->>'_application_id'
    AND coalesce(r.params->>'follow_up_number', '1') = coalesce(p.j->'params'->>'follow_up_number', '1')
);""")
    elif kind == "actions":
        actions = plan
        allowed = actions.get("allowed_ids")
        if not isinstance(allowed, dict):
            raise ValueError("actions must be produced by validate-actions")
        allowed_screen = _allowed_id_set(allowed, "screen")
        allowed_outreach = _allowed_id_set(allowed, "outreach")
        allowed_requests = _allowed_id_set(allowed, "requests")
        screens = _rows(actions, "screens", MAX_SCREEN)
        if not _unique_ids(screens, "screens", "job_id") <= allowed_screen:
            raise ValueError("screen job_id is outside validated allowed_ids")
        if screens:
            payload = _json_sql(screens)
            statements.append(f"""
WITH p AS (SELECT jsonb_array_elements({payload}) AS j)
INSERT INTO public.job_messages (scraped_job_id, message_type, content, generated_by, generated_at, profile_version, is_stale)
SELECT (j->>'job_id')::bigint, 'screen',
       (CASE j->>'decision' WHEN 'pass' THEN 'PASS: ' WHEN 'fail' THEN 'FAIL: ' ELSE 'REVIEW: ' END) || coalesce(j->>'reason', ''),
       'chatgpt-scheduled-task', now(), (j->>'profile_version')::integer,
       (j->>'profile_version') IS NULL FROM p
ON CONFLICT (scraped_job_id, message_type) DO UPDATE
SET content = excluded.content, generated_by = excluded.generated_by,
    generated_at = excluded.generated_at, profile_version = excluded.profile_version,
    is_stale = excluded.is_stale;
WITH p AS (SELECT jsonb_array_elements({payload}) AS j)
UPDATE public.scraped_jobs s SET dismissed = CASE WHEN p.j->>'decision' = 'fail' THEN 1 ELSE 0 END
FROM p WHERE s.id = (p.j->>'job_id')::bigint;""")
        outreach = _rows(actions, "outreach_drafts", MAX_OUTREACH)
        if not _unique_ids(outreach, "outreach_drafts", "job_id") <= allowed_outreach:
            raise ValueError("outreach job_id is outside validated allowed_ids")
        if outreach:
            payload = _json_sql(outreach)
            statements.append(f"""
WITH p AS (SELECT jsonb_array_elements({payload}) AS j)
INSERT INTO public.job_messages (scraped_job_id, message_type, content, generated_by, generated_at, profile_version, is_stale)
SELECT (j->>'job_id')::bigint, 'cold_dm', j->>'content',
       'chatgpt-scheduled-task', now(), (j->>'profile_version')::integer,
       (j->>'profile_version') IS NULL FROM p
ON CONFLICT (scraped_job_id, message_type) DO UPDATE
SET content = excluded.content, generated_by = excluded.generated_by,
    generated_at = excluded.generated_at, profile_version = excluded.profile_version,
    is_stale = excluded.is_stale;""")
        results = _rows(actions, "request_results", MAX_REQUESTS)
        if not _unique_ids(results, "request_results", "request_id") <= allowed_requests:
            raise ValueError("request_id is outside validated allowed_ids")
        if results:
            payload = _json_sql(results)
            statements.append(f"""
WITH p AS (SELECT jsonb_array_elements({payload}) AS j)
UPDATE public.message_requests r
SET status = p.j->>'status',
    content = CASE WHEN p.j->>'status' = 'ready' THEN p.j->>'content' ELSE NULL END,
    error = CASE WHEN p.j->>'status' = 'failed' THEN p.j->>'error' ELSE NULL END,
    completed_at = now()
FROM p WHERE r.id = (p.j->>'request_id')::bigint AND r.status = 'pending';""")
        letters = _rows(actions, "cover_letter_drafts", MAX_COVER_LETTERS)
        allowed_letters = _allowed_id_set(allowed, "cover_letters")
        if not _unique_ids(letters, "cover_letter_drafts", "job_id") <= allowed_letters:
            raise ValueError("cover-letter job_id is outside validated allowed_ids")
        if letters:
            payload = _json_sql(letters)
            statements.append(f"""
WITH p AS (SELECT jsonb_array_elements({payload}) AS j),
stale AS (
  UPDATE public.cover_letter_drafts d SET is_outdated = true
  FROM p WHERE d.scraped_job_id = (p.j->>'job_id')::bigint
    AND (d.resume_version IS DISTINCT FROM (p.j->>'resume_version')::integer
      OR d.jd_hash IS DISTINCT FROM p.j->>'jd_hash'
      OR d.generation_rules_version IS DISTINCT FROM p.j->>'rules_version')
  RETURNING d.id
)
INSERT INTO public.cover_letter_drafts
  (scraped_job_id, resume_profile_id, resume_version, jd_version, jd_hash,
   match_score, analysis_version, generation_rules_version, run_id, content,
   generated_by, generated_at, is_outdated)
SELECT (j->>'job_id')::bigint, (j->>'resume_profile_id')::bigint,
       (j->>'resume_version')::integer, (j->>'jd_version')::integer,
       j->>'jd_hash', (j->>'match_score')::integer, j->>'analysis_version',
       j->>'rules_version', '{run_id}', j->>'content',
       'chatgpt-scheduled-task', now(), false
FROM p
ON CONFLICT (scraped_job_id, resume_version, jd_hash, generation_rules_version)
DO NOTHING;""")
        statements.append(_notification_sql(actions.get("notification"), run_id, "run_summary", "run_summary"))
    else:
        raise ValueError("kind must be scrape, items, or actions")
    statements.append("COMMIT;")
    return "\n".join(statement for statement in statements if statement) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("scrape", "prepare", "sql"):
        cmd = sub.add_parser(name)
        cmd.add_argument("input")
        cmd.add_argument("output")
    validate = sub.add_parser("validate-actions")
    validate.add_argument("prepared")
    validate.add_argument("input")
    validate.add_argument("output")
    args = parser.parse_args()
    try:
        data = _read(args.input)
        if args.command == "validate-actions":
            result = validate_actions(_read(args.prepared), data)
            _write(args.output, result)
        elif args.command == "sql":
            Path(args.output).write_text(render_sql(data), encoding="utf-8")
        else:
            result = scrape_plan(data) if args.command == "scrape" else prepare_items(data)
            _write(args.output, result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"cloud_connector: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
