"""Pure persisted-application aggregations used by the dashboard and tests."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

POSITIVE_RESPONSE_STATUSES = {"Interview", "Interview Scheduled", "Interviewed", "Offer"}
STATUS_ORDER = (
    "Applied", "Follow-up Sent", "Assignment Submitted", "Interview",
    "Offer", "Rejected", "Ghosted", "Not Interested",
)


def _rows(rows):
    return [dict(row) for row in (rows or [])]


def attach_tracker_job_ids(applications, scraped_jobs):
    """Exact URL mapping; missing/deleted scraped records remain explicit None."""
    by_url = {row.get("url"): row.get("id") for row in _rows(scraped_jobs)
              if row.get("url") and type(row.get("id")) is int}
    return [{**row, "scraped_job_id": by_url.get(row.get("url"))}
            for row in _rows(applications)]


def weekly_trend(rows, weeks=12):
    buckets = defaultdict(lambda: {"Job": 0, "Internship": 0, "total": 0})
    for row in _rows(rows):
        try:
            value = date.fromisoformat(str(row.get("date_applied", ""))[:10])
        except ValueError:
            continue
        monday = value - timedelta(days=value.weekday())
        kind = "Internship" if str(row.get("type", "")).casefold() == "internship" else "Job"
        buckets[monday][kind] += 1
        buckets[monday]["total"] += 1
    result = []
    for monday in sorted(buckets)[-weeks:]:
        values = buckets[monday]
        result.append({"week": monday.isoformat(), "week_end": (monday + timedelta(days=6)).isoformat(), **values})
    return result


def platform_effectiveness(rows):
    groups = defaultdict(list)
    for row in _rows(rows):
        groups[str(row.get("platform") or "Unknown").strip() or "Unknown"].append(row)
    result = []
    for platform, values in groups.items():
        responses = sum(row.get("status") in POSITIVE_RESPONSE_STATUSES for row in values)
        applications = len(values)
        result.append({
            "platform": platform, "applications": applications,
            "responses": responses,
            "response_rate": round(responses * 100 / applications, 1),
        })
    return sorted(result, key=lambda row: (-row["applications"], row["platform"].casefold()))


def status_breakdown(rows):
    rows = _rows(rows)
    if not rows:
        return {}
    counts = Counter(str(row.get("status") or "Unknown") for row in rows)
    result = {status: counts.pop(status, 0) for status in STATUS_ORDER}
    for status in sorted(counts):
        result[status] = counts[status]
    return result


_ROLE_FAMILIES = (
    ("Generative AI / LLM", r"\b(?:gen(?:erative)?\s*ai|llm|rag|language model|prompt)\b"),
    ("Machine Learning", r"\b(?:machine learning|ml|deep learning)\b"),
    ("Data Science", r"\b(?:data scientist|data science)\b"),
    ("NLP", r"\b(?:nlp|natural language)\b"),
    ("Cloud / MLOps", r"\b(?:mlops|cloud|aws|azure|gcp|platform engineer)\b"),
    ("Backend / Python", r"\b(?:backend|python|fastapi|api engineer)\b"),
    ("AI Engineering", r"\b(?:artificial intelligence|ai)\b"),
)


def role_family(role):
    normalized = re.sub(r"[^a-z0-9+#/.]+", " ", str(role or "").casefold()).strip()
    for label, pattern in _ROLE_FAMILIES:
        if re.search(pattern, normalized):
            return label
    return "Other / unclassified"


def role_analysis(rows):
    groups = defaultdict(list)
    for row in _rows(rows):
        groups[role_family(row.get("role"))].append(row)
    result = []
    for family, values in groups.items():
        responses = sum(row.get("status") in POSITIVE_RESPONSE_STATUSES for row in values)
        applied = len(values)
        examples = sorted({str(row.get("role") or "").strip() for row in values if row.get("role")})[:3]
        result.append({
            "role_keyword": family, "applied": applied, "responses": responses,
            "response_rate": round(responses * 100 / applied, 1),
            "example_roles": examples,
        })
    return sorted(result, key=lambda row: (-row["applied"], row["role_keyword"]))
