"""
Outreach messages for scraped jobs, written by the scheduled Claude routine.

There is no hosted LLM call here. The routine session *is* Claude: it lists the
jobs that still need a message, writes each one itself, and saves it back. This
script is the interface it drives.

    # what still needs a message (JSON: profile + jobs)
    python pending_messages.py list --limit 10

    # save one message (body on stdin avoids shell-quoting multi-line text)
    python pending_messages.py save --job-id 4821 < message.txt

Requires SUPABASE_URL and SUPABASE_KEY. No LLM key of any kind.
"""

import argparse
import json
import sys

from tracker import (
    DEFAULT_MESSAGE_TYPE,
    get_job_message,
    get_jobs_needing_messages,
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

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
