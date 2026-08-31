"""
Outreach messages for scraped jobs, written by the scheduled Claude routine.

There is no hosted LLM call here. The routine session *is* Claude: it lists the
jobs that still need a message, writes each one itself, and saves it back. This
script is the interface it drives.

    # what still needs a message (JSON: profile + jobs)
    python pending_messages.py list --limit 10

    # save one message (body on stdin avoids shell-quoting multi-line text)
    python pending_messages.py save --job-id 4821 < message.txt

    # freeform requests queued from the UI, each with its ready-made prompt
    python pending_messages.py requests
    python pending_messages.py fulfil --request-id 12 < message.txt

    # end-of-run summary: in-app notification + web push to the installed PWA
    python pending_messages.py notify --title "Hourly run" --body "3 jobs, 3 DMs"

Requires SUPABASE_URL and SUPABASE_KEY. No LLM key of any kind.
"""

import argparse
import json
import sys

from tracker import (
    DEFAULT_MESSAGE_TYPE,
    complete_message_request,
    fail_message_request,
    get_job_message,
    get_message_request,
    get_message_requests,
    save_job_message,
)
from tracker import save_notification, send_push_notifications


def _profile_text():
    """Profile context for writing the message, from the DB or the fallback."""
    try:
        from message_generator import _get_profile_text
        return _get_profile_text()
    except Exception:
        return ""


def _tracked_jobs_missing(message_type, limit):
    """Tracker-logged scraped jobs lacking a stored message of this type.

    Content is generated ONLY for jobs the user logged to the tracker (an
    application row whose URL matches a scraped job, terminal statuses
    excluded), newest first. Returns (jobs, tracked_total).
    """
    from tracker import TERMINAL_STATUSES, _get_client, get_job_message

    db = _get_client()
    apps = db.table("applications").select("url,status").execute().data or []
    urls = [a["url"] for a in apps
            if (a.get("url") or "").strip()
            and a.get("status") not in TERMINAL_STATUSES]

    tracked = []
    for i in range(0, len(urls), 100):
        resp = (db.table("scraped_jobs")
                .select("id, title, company, location, url, description")
                .in_("url", urls[i:i + 100])
                .execute())
        tracked.extend(resp.data or [])

    need = []
    for r in sorted(tracked, key=lambda r: r["id"], reverse=True):
        if len(need) >= limit:
            break
        if get_job_message(r["id"], message_type=message_type):
            continue
        r["description"] = (r.get("description") or "").strip()
        need.append(r)
    return need, len(tracked)


def cmd_list(args):
    jobs, tracked_total = _tracked_jobs_missing(args.type, args.limit)
    json.dump(
        {
            "message_type": args.type,
            "tracked_jobs_total": tracked_total,
            "profile": _profile_text(),
            "jobs": jobs,
        },
        sys.stdout,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


def cmd_save(args):
    content = (args.content if args.content is not None else sys.stdin.read()).strip()
    if not content:
        print("Refusing to save an empty message.", file=sys.stderr)
        return 1

    ok = save_job_message(args.job_id, content, message_type=args.type)
    if not ok:
        return 1

    saved = get_job_message(args.job_id, message_type=args.type)
    if not saved:
        print(f"Save reported success but job {args.job_id} has no row.", file=sys.stderr)
        return 1

    print(f"Saved {args.type} for job {args.job_id} ({len(content)} chars).")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="jobs with no stored message yet")
    p_list.add_argument("--limit", type=int, default=10)
    p_list.add_argument("--type", default=DEFAULT_MESSAGE_TYPE)
    p_list.set_defaults(func=cmd_list)

    p_save = sub.add_parser("save", help="store a message for one job")
    p_save.add_argument("--job-id", type=int, required=True)
    p_save.add_argument("--type", default=DEFAULT_MESSAGE_TYPE)
    p_save.add_argument("--content", default=None,
                        help="message text; omit to read from stdin")
    p_save.set_defaults(func=cmd_save)

    p_fup = sub.add_parser(
        "followups",
        help="queue follow-up requests for tracked applications now due",
    )
    p_fup.set_defaults(func=cmd_followups)

    p_req = sub.add_parser("requests", help="pending UI requests, with prompts")
    p_req.add_argument("--limit", type=int, default=20)
    p_req.set_defaults(func=cmd_requests)

    p_ful = sub.add_parser("fulfil", help="answer one queued request")
    p_ful.add_argument("--request-id", type=int, required=True)
    p_ful.add_argument("--content", default=None,
                       help="message text; omit to read from stdin")
    p_ful.set_defaults(func=cmd_fulfil)

    p_fail = sub.add_parser("fail", help="mark a request failed")
    p_fail.add_argument("--request-id", type=int, required=True)
    p_fail.add_argument("--error", required=True)
    p_fail.set_defaults(func=cmd_fail)

    p_dem = sub.add_parser(
        "demos",
        help="tracker-logged jobs still lacking a live demo",
    )
    p_dem.add_argument("--limit", type=int, default=4)
    p_dem.set_defaults(func=cmd_demos)

    p_cos = sub.add_parser(
        "companies",
        help="recent-job companies with no fresh intel cached",
    )
    p_cos.add_argument("--limit", type=int, default=10)
    p_cos.set_defaults(func=cmd_companies)

    p_sco = sub.add_parser("save-company", help="store company intel (JSON on stdin)")
    p_sco.add_argument("--name", required=True)
    p_sco.set_defaults(func=cmd_save_company)

    p_int = sub.add_parser("intel", help="print cached company intel as JSON")
    p_int.add_argument("--name", required=True)
    p_int.set_defaults(func=cmd_intel)

    p_scrl = sub.add_parser("screen-list", help="scraped jobs not yet resume-screened")
    p_scrl.add_argument("--limit", type=int, default=100)
    p_scrl.set_defaults(func=cmd_screen_list)

    p_scr = sub.add_parser("screen", help="record a resume-screening decision")
    p_scr.add_argument("--job-id", type=int, required=True)
    p_scr.add_argument("--decision", choices=["pass", "fail"], required=True)
    p_scr.add_argument("--reason", default="")
    p_scr.set_defaults(func=cmd_screen)

    p_not = sub.add_parser("notify", help="in-app notification + web push")
    p_not.add_argument("--title", required=True)
    p_not.add_argument("--body", required=True)
    p_not.add_argument("--url", default="/tonight")
    p_not.set_defaults(func=cmd_notify)

    args = parser.parse_args()
    sys.exit(args.func(args))


def _build_prompt(message_type, params):
    """Render the stored request into the prompt the app would have sent."""
    from message_generator import PROMPT_BUILDERS

    builder = PROMPT_BUILDERS.get(message_type)
    if builder is None:
        return {"error": f"unknown message_type {message_type!r}"}
    try:
        # Keys starting with "_" are request metadata (e.g. _application_id
        # linking an auto-queued follow-up to its tracker row), not builder args.
        clean = {k: v for k, v in (params or {}).items() if not k.startswith("_")}
        return builder(**clean)
    except TypeError as e:
        return {"error": f"params do not match {message_type} builder: {e}"}


def cmd_requests(args):
    rows = get_message_requests(status="pending", limit=args.limit)
    out = []
    for r in rows:
        spec = _build_prompt(r["message_type"], r.get("params"))
        out.append({
            "request_id": r["id"],
            "message_type": r["message_type"],
            "created_at": r.get("created_at"),
            **spec,
        })
    json.dump({"pending": out}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_fulfil(args):
    row = get_message_request(args.request_id)
    if not row:
        print(f"No request {args.request_id}.", file=sys.stderr)
        return 1

    content = (args.content if args.content is not None else sys.stdin.read()).strip()
    if not content:
        print("Refusing to save an empty message.", file=sys.stderr)
        return 1

    # Apply the same sentence-boundary trim the old inline generator used.
    from message_generator import enforce_char_limit
    spec = _build_prompt(row["message_type"], row.get("params"))
    content = enforce_char_limit(content, spec.get("char_limit"))

    if not complete_message_request(args.request_id, content):
        return 1
    print(f"Request {args.request_id} ({row['message_type']}) ready — {len(content)} chars.")
    return 0


def cmd_followups(args):
    """Queue a follow-up request for each tracked application whose
    follow_up_date has arrived.

    One request per application per follow-up round: an application already
    holding a pending/ready request for its current round is skipped, and
    rounds stop after the third follow-up (the builder's final-tone cap).
    The queued requests are then written by the normal `requests`/`fulfil`
    flow in the same routine run.
    """
    from datetime import date, datetime

    from tracker import (
        create_message_request,
        get_follow_up_history,
        get_follow_ups_due,
    )

    df = get_follow_ups_due()
    apps = [] if df is None or df.empty else df.to_dict("records")

    existing = get_message_requests(limit=200)
    already = set()
    for r in existing:
        p = r.get("params") or {}
        if (
            r.get("message_type") == "follow-up"
            and r.get("status") in ("pending", "ready")
            and p.get("_application_id")
        ):
            already.add((p["_application_id"], p.get("follow_up_number", 1)))

    queued, skipped = [], 0
    for app in apps:
        history = get_follow_up_history("application", app["id"]) or []
        number = len(history) + 1
        if number > 3 or (app["id"], number) in already:
            skipped += 1
            continue

        days = 7
        try:
            applied = datetime.strptime(
                str(app.get("date_applied", ""))[:10], "%Y-%m-%d"
            ).date()
            days = max((date.today() - applied).days, 1)
        except (ValueError, TypeError):
            pass

        previous = [
            h.get("message_content", "")
            for h in sorted(history, key=lambda h: h.get("sent_at") or "")
        ][-3:]

        row = create_message_request("follow-up", {
            "company_name": app.get("company", ""),
            "role_title": app.get("role", ""),
            "days_since_applied": days,
            "original_platform": app.get("platform") or "LinkedIn",
            "follow_up_number": number,
            "previous_messages": [m for m in previous if m],
            "_application_id": app["id"],
        })
        if row:
            queued.append({
                "request_id": row["id"],
                "application_id": app["id"],
                "company": app.get("company", ""),
                "role": app.get("role", ""),
                "follow_up_number": number,
            })

    json.dump({"queued": queued, "skipped": skipped}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_demos(args):
    """List tracker-logged jobs that still lack a live demo.

    Every tracked job eventually gets a demo; --limit just bounds one
    firing's batch.
    """
    jobs, tracked_total = _tracked_jobs_missing("demo_html", args.limit)
    need = [{
        "job_id": r["id"],
        "title": r.get("title", ""),
        "company": r.get("company", ""),
        "description": r.get("description", ""),
    } for r in jobs]

    json.dump(
        {
            "profile": _profile_text(),
            "tracked_jobs_total": tracked_total,
            "jobs_needing_demos": need,
        },
        sys.stdout,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


def cmd_companies(args):
    """List companies from recent scraped jobs that have no fresh intel cached.

    The routine writes a short intel blurb for each (from its own knowledge)
    and saves it with `save-company`.
    """
    from datetime import datetime, timedelta

    from tracker import _get_client, get_cached_research

    since = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    db = _get_client()
    resp = (db.table("scraped_jobs").select("company")
            .gte("scraped_at", since)
            .eq("dismissed", 0)
            .execute())
    companies = sorted({(r.get("company") or "").strip()
                        for r in (resp.data or []) if (r.get("company") or "").strip()})

    missing = []
    for c in companies:
        if len(missing) >= args.limit:
            break
        if get_cached_research(c) is None:
            missing.append(c)

    json.dump({"companies_needing_intel": missing}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_intel(args):
    """Print cached company intel as JSON so agents can self-serve the email
    domain (from product_url) and hiring contact without threading state
    through the orchestrator. Prints {"found": false} when nothing is cached."""
    from tracker import get_cached_research

    row = get_cached_research(args.name)
    if not row:
        print(json.dumps({"found": False}))
        return 0
    print(json.dumps({"found": True, **row}, default=str))
    return 0


def cmd_screen_list(args):
    """Visible scraped jobs not yet screened against the resume, newest first,
    with the candidate's profile. Claude reads each and decides fit + level."""
    from tracker import get_scraped_jobs, get_job_message

    df = get_scraped_jobs()
    rows = df.to_dict("records") if not df.empty else []
    need = []
    for r in rows:
        if len(need) >= args.limit:
            break
        if get_job_message(r["id"], message_type="screen"):
            continue
        need.append({
            "id": r["id"],
            "title": r.get("title", ""),
            "company": r.get("company", ""),
            "location": r.get("location", ""),
            "url": r.get("url", ""),
            "description": (r.get("description") or "").strip(),
        })
    json.dump({"profile": _profile_text(), "jobs": need}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_screen(args):
    """Record a resume-screening decision for one scraped job. A 'fail'
    dismisses the job (hidden everywhere, kept for URL dedup); either way the
    decision is stored as a 'screen' message so it is not re-screened."""
    from tracker import save_job_message, mark_scraped_job

    decision = args.decision
    tag = ("PASS: " if decision == "pass" else "FAIL: ") + (args.reason or "")
    save_job_message(args.job_id, tag.strip(), message_type="screen")
    if decision == "fail":
        mark_scraped_job(args.job_id, "dismissed")
    else:
        # A PASS must make the job visible even if a prior FAIL had hidden it
        # (re-screens across rule changes), so explicitly un-dismiss.
        mark_scraped_job(args.job_id, "keep")
    print(f"Screened job {args.job_id}: {decision}. {args.reason or ''}".strip())
    return 0


def cmd_save_company(args):
    """Save company intel from stdin JSON into company_research_cache.

    Expected JSON: {"description": str, "recent_news": str,
                    "tech_signals": [str, ...], "product_url": str}
    Unknown/uncertain fields should simply be omitted or empty.
    """
    from tracker import save_research_cache

    raw = sys.stdin.read().strip()
    if not raw:
        print("Refusing to save empty intel.", file=sys.stderr)
        return 1
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"stdin is not valid JSON: {e}", file=sys.stderr)
        return 1
    if not (data.get("description") or "").strip():
        print("Intel needs a non-empty 'description'.", file=sys.stderr)
        return 1

    save_research_cache(args.name, {
        "description": data.get("description", ""),
        "recent_news": data.get("recent_news", ""),
        "tech_signals": data.get("tech_signals", []) or [],
        "product_url": data.get("product_url", ""),
        "hiring_contact": data.get("hiring_contact", {}) or {},
    })
    print(f"Saved intel for {args.name}.")
    return 0


def cmd_fail(args):
    if not fail_message_request(args.request_id, args.error):
        return 1
    print(f"Request {args.request_id} marked failed.")
    return 0


def cmd_notify(args):
    """Save an in-app notification and push it to every subscribed device.

    The routine calls this once at the very end of each run — after the DMs are
    written — so the push can carry the whole summary and fires even when the
    scrape found nothing. Push delivery needs VAPID_PRIVATE_KEY and
    VAPID_CLAIM_EMAIL; without them send_push_notifications() prints a notice
    and skips, and the in-app notification is still saved.
    """
    try:
        save_notification(
            title=args.title,
            body=args.body,
            notification_type="run_summary",
        )
        print("In-app notification saved.")
    except Exception as e:
        print(f"Could not save in-app notification: {e}", file=sys.stderr)

    try:
        send_push_notifications(title=args.title, body=args.body, url=args.url)
    except Exception as e:
        print(f"Could not send push: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    main()
