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
    get_jobs_needing_messages,
    get_message_request,
    get_message_requests,
    save_job_message,
)


def _profile_text():
    """Profile context for writing the message, from the DB or the fallback."""
    try:
        from message_generator import _get_profile_text
        return _get_profile_text()
    except Exception:
        return ""


def cmd_list(args):
    jobs = get_jobs_needing_messages(limit=args.limit, message_type=args.type)
    for j in jobs:
        # Descriptions are capped at 500 chars upstream; keep them whole here.
        j["description"] = (j.get("description") or "").strip()
    json.dump(
        {"message_type": args.type, "profile": _profile_text(), "jobs": jobs},
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

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()


def _build_prompt(message_type, params):
    """Render the stored request into the prompt the app would have sent."""
    from message_generator import PROMPT_BUILDERS

    builder = PROMPT_BUILDERS.get(message_type)
    if builder is None:
        return {"error": f"unknown message_type {message_type!r}"}
    try:
        return builder(**(params or {}))
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


def cmd_fail(args):
    if not fail_message_request(args.request_id, args.error):
        return 1
    print(f"Request {args.request_id} marked failed.")
    return 0
