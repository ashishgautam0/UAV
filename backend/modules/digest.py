"""
Build the job-scrape digest.

Produces the markdown table that is saved to Supabase (email_logs) and served
by /api/tonight/emails. Delivery lived here too until the Gmail integration was
removed; this module only builds content now.
"""

import re


def _detect_paid_status(text):
    """Detect if internship is paid or unpaid from description."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["unpaid", "no stipend", "voluntary", "volunteer"]):
        return "Unpaid"
    if any(kw in text_lower for kw in [
        "paid", "stipend", "salary", "compensation", "ctc",
        "per month", "/month", "lpa", "inr", "usd", "$",
    ]):
        return "Paid"
    return "-"


def _detect_duration(text):
    """Extract internship duration from description."""
    text_lower = text.lower()
    # Match patterns like "3 months", "6-month", "2 month duration"
    match = re.search(r'(\d+)\s*[-–]?\s*months?', text_lower)
    if match:
        return f"{match.group(1)} months"
    match = re.search(r'(\d+)\s*[-–]?\s*weeks?', text_lower)
    if match:
        return f"{match.group(1)} weeks"
    match = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*months?', text_lower)
    if match:
        return f"{match.group(1)}-{match.group(2)} months"
    return "-"


def _job_row(j: dict) -> str:
    """Build a single markdown table row matching the website card fields."""
    title   = j.get("title", "Untitled").replace("|", "/").strip()[:50]
    company = j.get("company", "-").replace("|", "/").strip()[:25]
    location = j.get("location", "-").replace("|", "/").strip()[:20]
    score   = j.get("score", 0)
    verdict = (j.get("verdict") or "-").replace("|", "/").strip()[:15]
    ats     = j.get("ats_score") or "-"
    mode    = (j.get("work_mode") or "-").replace("|", "/").strip()[:10]
    source  = j.get("source", "-").replace("|", "/").strip()[:15]
    url     = j.get("url", "")
    link    = f"[Apply]({url})" if url else "-"
    reason  = (j.get("llm_reason") or "").replace("|", "/").strip()[:80]
    reason_cell = f"_{reason}_" if reason else "-"
    return f"| {title} | {company} | {location} | {mode} | {verdict} | {score} | {ats} | {source} | {reason_cell} | {link} |"


_TABLE_HEADER = "| Title | Company | Location | Mode | Verdict | Score | ATS | Source | Reason | Link |"
_TABLE_SEP    = "|-------|---------|----------|------|---------|-------|-----|--------|--------|------|"


def build_email_content(jobs, sources_status, sources_errors=None):
    """Build markdown table for the email — identical to the website job cards."""
    lines = []

    if not jobs:
        lines.append("No new internships found.")
        return "\n".join(lines)

    # Only show jobs that passed the filter (same as the website)
    filtered_jobs = [j for j in jobs if j.get("filtered", True)]

    if not filtered_jobs:
        lines.append("No new internships found.")
        return "\n".join(lines)

    lines.append(f"### New Jobs ({len(filtered_jobs)})")
    lines.append("")
    lines.append(_TABLE_HEADER)
    lines.append(_TABLE_SEP)
    for j in filtered_jobs:
        lines.append(_job_row(j))

    return "\n".join(lines)


def get_alert_number():
    """Get the next alert number from existing email logs."""
    try:
        from tracker import get_email_logs
        logs = get_email_logs(limit=1)
        if logs:
            # Extract number from last subject like "Job Alert #5"
            last_subject = logs[0].get("subject", "")
            match = re.search(r'#(\d+)', last_subject)
            if match:
                return int(match.group(1)) + 1
        return 1
    except Exception:
        return 1
