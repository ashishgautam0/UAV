"""Deterministic draft checks; semantic grounding still requires review."""
import re

_DEMO_LINK = re.compile(r"/api/demo/(\d+)")
_DEMO_LINKED_KINDS = {"cold_dm", "cold-dm", "hr_email"}


def wrong_demo_links(content, scraped_job_id):
    """Demo ids in the draft that belong to a different job.

    A draft reused across two jobs carries the first job's demo link, which
    would point the second employer at a demo built for someone else's role.
    """
    if scraped_job_id is None:
        return []
    return sorted({
        found for found in _DEMO_LINK.findall(content or "")
        if found != str(scraped_job_id)
    })


def validate_outreach_draft(kind, content, scraped_job_id=None):
    if kind in _DEMO_LINKED_KINDS:
        foreign = wrong_demo_links(content, scraped_job_id)
        if foreign:
            return (f"Draft for job {scraped_job_id} links demo(s) "
                    f"{', '.join(foreign)}; write this job's own note.")
    if kind in {"cold_dm", "cold-dm"}:
        if len(content.encode("utf-16-le")) // 2 > 300:
            return "Connection note exceeds 300 characters; rewrite, do not truncate."
        if re.search(r"(?im)^\s*(?:variant\s*\d|subject\s*:|to\s*:|```)", content):
            return "Save one connection note only, without variants, headers or code fences."
        if re.search(r"(?i)(?:resume|cv|pdf).{0,30}attach|attach.{0,30}(?:resume|cv|pdf)", content):
            return "Connection notes cannot attach a resume."
    return None
