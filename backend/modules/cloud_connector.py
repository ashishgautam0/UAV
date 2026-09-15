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
import json
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
MAX_EXISTING_URLS = 20_000
MAX_SCREEN = 100
MAX_OUTREACH = 10
MAX_REQUESTS = 20
MAX_DUE_APPLICATIONS = 100
MAX_HISTORY = 500
MAX_ACTIVE_REQUESTS = 200


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


def profile_text(row):
    """Mirror profile.py/message_generator.py without opening a DB connection."""
    row = row or {}
    resume = (row.get("resume_text") or "").strip()
    if len(resume) >= 200:
        return resume
    lines = []
    for exp in row.get("experience") or []:
        lines.append(f"- {exp.get('role', '')} at {exp.get('company', '')} ({exp.get('period', '')}): {exp.get('description', '')}")
    if row.get("education"):
        lines.append(f"- {row['education']}")
    for project in row.get("projects") or []:
        lines.append(f"- Built {project.get('name', '')}: {project.get('description', '')}")
    if row.get("skills"):
        lines.append(f"- Tech stack: {', '.join(row['skills'])}")
    if row.get("location_preference"):
        lines.append(f"- Location preference: {row['location_preference']}")
    if row.get("target_roles"):
        lines.append(f"- Looking for: {', '.join(row['target_roles'])}")
    if lines:
        return "\n".join(lines)
    from message_generator import SUBIDH_PROFILE
    return SUBIDH_PROFILE


def _next_alert(subject):
    match = re.search(r"#(\d+)", subject or "")
    return int(match.group(1)) + 1 if match else 1


def scrape_plan(context):
    """Run the existing scraper/filter pipeline without database credentials."""
    urls = context.get("existing_job_urls", [])
    if not isinstance(urls, list) or len(urls) > MAX_EXISTING_URLS:
        raise ValueError(f"existing_job_urls must contain at most {MAX_EXISTING_URLS} values")
    existing = {url for url in urls if isinstance(url, str) and url}

    from digest import build_email_content
    from hourly import _experience_ok, _matches_desired_title, _nationality_ok, _resume_fit_filter
    from scraper import check_apply_type, run_all_scrapers

    resume = profile_text(context.get("user_profile"))
    jobs, sources_status, sources_errors = run_all_scrapers()
    new_jobs = [job for job in jobs if job.get("url", "") not in existing]
    counts = {"found": len(jobs), "after_dedup": len(new_jobs)}
    new_jobs = [job for job in new_jobs if _matches_desired_title(job.get("title", ""))]
    counts["after_title"] = len(new_jobs)
    new_jobs = [job for job in new_jobs if _experience_ok(job.get("description", ""))]
    counts["after_experience"] = len(new_jobs)
    new_jobs = [job for job in new_jobs if _nationality_ok(job.get("description", ""))]
    counts["after_nationality"] = len(new_jobs)
    new_jobs, resume_note = _resume_fit_filter(new_jobs, resume)
    counts["after_resume_net"] = len(new_jobs)

    try:
        from jd_analyzer import full_analyze, quick_ats
        for job in new_jobs[:15]:
            try:
                result = full_analyze(job.get("title", ""), job.get("description", ""))
                job["ats_score"] = quick_ats(job.get("description", ""), resume)
                job["skill_match"] = result.get("skills", {}).get("match_percentage", 0)
                job["noc_verdict"] = result.get("noc", {}).get("confidence", "")
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
               "score", "noc_verdict", "skill_match", "verdict", "ats_score")
    db_jobs = [{key: job.get(key, "" if key not in {"score", "skill_match", "ats_score"} else 0)
                for key in allowed} for job in new_jobs]
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
    return {"schema_version": SCHEMA_VERSION, "kind": "scrape", "jobs": db_jobs,
            "email_log": email_log, "notification": notification, "health_notification": health,
            "stats": {**counts, "resume_net": resume_note, "sources": sources_status,
                      "source_errors": sources_errors}}


def prepare_items(context):
    """Prepare bounded screening/drafting work and idempotent follow-up inserts."""
    profile = profile_text(context.get("user_profile"))
    screen = _rows(context, "screen_jobs", MAX_SCREEN)
    outreach = _rows(context, "outreach_jobs", MAX_OUTREACH)
    pending = _rows(context, "pending_requests", MAX_REQUESTS)
    due = _rows(context, "due_applications", MAX_DUE_APPLICATIONS)
    history = _rows(context, "follow_up_history", MAX_HISTORY)
    active = _rows(context, "active_followup_requests", MAX_ACTIVE_REQUESTS)

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
    return {"schema_version": SCHEMA_VERSION, "kind": "items", "profile": profile,
            "screen_jobs": screen, "outreach_jobs": outreach, "requests": requests,
            "followup_requests": followups}


def validate_actions(actions):
    """Validate response JSON before the connector performs writes."""
    screens = _rows(actions, "screens", MAX_SCREEN)
    outreach = _rows(actions, "outreach_drafts", MAX_OUTREACH)
    results = _rows(actions, "request_results", MAX_REQUESTS)
    for row in screens:
        if not isinstance(row.get("job_id"), int) or row.get("decision") not in ("pass", "fail"):
            raise ValueError("each screen needs integer job_id and pass/fail decision")
    for row in outreach:
        if not isinstance(row.get("job_id"), int) or not (row.get("content") or "").strip():
            raise ValueError("each outreach draft needs integer job_id and non-empty content")
    for row in results:
        if not isinstance(row.get("request_id"), int) or row.get("status") not in ("ready", "failed"):
            raise ValueError("each request result needs integer request_id and ready/failed status")
        field = "content" if row["status"] == "ready" else "error"
        if not (row.get(field) or "").strip():
            raise ValueError(f"request {row['request_id']} needs non-empty {field}")
    return {"schema_version": SCHEMA_VERSION, "kind": "actions", "screens": screens,
            "outreach_drafts": outreach, "request_results": results,
            "notification": actions.get("notification")}


def _json_sql(value):
    """Return an injection-safe jsonb expression (payload is base64, never SQL text)."""
    encoded = base64.b64encode(json.dumps(value, ensure_ascii=False).encode("utf-8")).decode("ascii")
    return f"convert_from(decode('{encoded}', 'base64'), 'UTF8')::jsonb"


def _notification_sql(row):
    if not row:
        return ""
    payload = _json_sql(row)
    return f"""
WITH p AS (SELECT {payload} AS j)
INSERT INTO public.notifications (title, body, type, metadata)
SELECT j->>'title', j->>'body', coalesce(j->>'type', 'run_summary'), coalesce(j->'metadata', '{{}}'::jsonb)
FROM p
WHERE NOT EXISTS (
  SELECT 1 FROM public.notifications n
  WHERE n.title = p.j->>'title' AND n.body = p.j->>'body'
    AND n.created_at >= now() - interval '2 hours'
);"""


def render_sql(plan):
    """Render an allowlisted mutation plan as one transaction.

    Values travel as base64-encoded JSON and are decoded by PostgreSQL.  No
    model-generated string is interpolated as SQL syntax or an identifier.
    """
    kind = plan.get("kind")
    statements = ["BEGIN;"]
    if kind == "scrape":
        jobs = _rows(plan, "jobs", 500)
        if jobs:
            payload = _json_sql(jobs)
            statements.append(f"""
WITH p AS (SELECT jsonb_array_elements({payload}) AS j)
INSERT INTO public.scraped_jobs
  (title, company, location, source, url, description, score, noc_verdict, skill_match, verdict, ats_score)
SELECT j->>'title', j->>'company', j->>'location', j->>'source', j->>'url',
       j->>'description', coalesce((j->>'score')::integer, 0), coalesce(j->>'noc_verdict', ''),
       coalesce((j->>'skill_match')::integer, 0), coalesce(j->>'verdict', ''),
       coalesce((j->>'ats_score')::integer, 0)
FROM p WHERE nullif(j->>'url', '') IS NOT NULL
ON CONFLICT (url) DO NOTHING;""")
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
        statements.append(_notification_sql(plan.get("notification")))
        statements.append(_notification_sql(plan.get("health_notification")))
    elif kind == "items":
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
        actions = validate_actions(plan)
        screens = actions["screens"]
        if screens:
            payload = _json_sql(screens)
            statements.append(f"""
WITH p AS (SELECT jsonb_array_elements({payload}) AS j)
INSERT INTO public.job_messages (scraped_job_id, message_type, content, generated_by, generated_at)
SELECT (j->>'job_id')::bigint, 'screen',
       (CASE WHEN j->>'decision' = 'pass' THEN 'PASS: ' ELSE 'FAIL: ' END) || coalesce(j->>'reason', ''),
       'chatgpt-scheduled-task', now() FROM p
ON CONFLICT (scraped_job_id, message_type) DO UPDATE
SET content = excluded.content, generated_by = excluded.generated_by, generated_at = excluded.generated_at;
WITH p AS (SELECT jsonb_array_elements({payload}) AS j)
UPDATE public.scraped_jobs s SET dismissed = CASE WHEN p.j->>'decision' = 'fail' THEN 1 ELSE 0 END
FROM p WHERE s.id = (p.j->>'job_id')::bigint;""")
        outreach = actions["outreach_drafts"]
        if outreach:
            payload = _json_sql(outreach)
            statements.append(f"""
WITH p AS (SELECT jsonb_array_elements({payload}) AS j)
INSERT INTO public.job_messages (scraped_job_id, message_type, content, generated_by, generated_at)
SELECT (j->>'job_id')::bigint, coalesce(j->>'message_type', 'cold_dm'), j->>'content',
       'chatgpt-scheduled-task', now() FROM p
ON CONFLICT (scraped_job_id, message_type) DO UPDATE
SET content = excluded.content, generated_by = excluded.generated_by, generated_at = excluded.generated_at;""")
        results = actions["request_results"]
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
        statements.append(_notification_sql(actions.get("notification")))
    else:
        raise ValueError("kind must be scrape, items, or actions")
    statements.append("COMMIT;")
    return "\n".join(statement for statement in statements if statement) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("scrape", "prepare", "validate-actions", "sql"):
        cmd = sub.add_parser(name)
        cmd.add_argument("input")
        cmd.add_argument("output")
    args = parser.parse_args()
    try:
        data = _read(args.input)
        if args.command == "sql":
            Path(args.output).write_text(render_sql(data), encoding="utf-8")
        else:
            result = scrape_plan(data) if args.command == "scrape" else prepare_items(data) if args.command == "prepare" else validate_actions(data)
            _write(args.output, result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"cloud_connector: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
