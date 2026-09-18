"""Explainable application priority built on the reviewed active profile.

Priority is separate from PDF readability, mandatory eligibility, and
resume-to-JD match. Freshness and application ease are used only after a real
match score exists; unknown evidence never becomes a fabricated high score.
"""

import re
from datetime import datetime, timezone

W_MATCH = 0.75
W_FRESH = 0.18
W_EASE = 0.07

_STOP = {
    "the", "and", "for", "with", "you", "our", "are", "will", "your", "that",
    "this", "have", "from", "job", "role", "work", "team", "who", "all", "not",
    "but", "can", "has", "was", "were", "they", "their", "them", "out", "any",
    "per", "may", "via", "etc", "such", "into", "onto", "over", "under", "www",
    "http", "https", "com", "join", "about", "apply", "years", "year", "plus",
    "strong", "good", "great", "help", "using", "able", "must", "should",
    "looking", "candidate", "candidates", "experience", "requirements",
    "responsibilities", "including", "ability", "knowledge", "skills",
    "preferred", "required", "position", "company", "opportunity",
}


def _tokens(text):
    return {
        token for token in re.split(r"[^a-z0-9+#.]+", (text or "").lower())
        if len(token) > 2 and token not in _STOP
    }


def _fit_from_lexical(profile_tokens, jd_text, title):
    """Legacy coarse pre-net only; final ranking uses explainable matching."""
    if not profile_tokens:
        return 0.0
    jd = _tokens(jd_text)
    if not jd:
        return 0.0
    overlap = profile_tokens & jd
    return min(
        len(overlap) / 12.0
        + min(len(profile_tokens & _tokens(title)) * 0.08, 0.24),
        1.0,
    )


def _freshness(scraped_at):
    if not scraped_at:
        return 0.5
    try:
        value = datetime.fromisoformat(str(scraped_at).replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.5
    hours = (datetime.now(timezone.utc) - value).total_seconds() / 3600.0
    return max(0.2, min(1.0, 1.0 - hours / 48.0))


def compute_application_priority(job, analysis):
    """Return (0..100 or None, explanation) without personal bonus rules."""
    match_score = (analysis.get("resume_jd_match") or {}).get("score")
    eligibility = (analysis.get("mandatory_eligibility") or {}).get("status", "unknown")
    fresh = _freshness(job.get("scraped_at"))
    ease = 1.0 if job.get("verdict") == "EASY_APPLY" else 0.55

    if eligibility == "not_met":
        return 0.0, {
            "match": match_score,
            "eligibility": eligibility,
            "freshness": round(fresh, 3),
            "ease": round(ease, 3),
            "score": 0.0,
            "reason": "An explicit mandatory requirement is not met.",
        }
    if eligibility == "unknown":
        return None, {
            "match": match_score,
            "eligibility": eligibility,
            "freshness": round(fresh, 3),
            "ease": round(ease, 3),
            "score": None,
            "reason": "A mandatory criterion is unknown and needs review.",
        }
    if match_score is None:
        return None, {
            "match": None,
            "eligibility": eligibility,
            "freshness": round(fresh, 3),
            "ease": round(ease, 3),
            "score": None,
            "reason": "Insufficient profile or job-description evidence.",
        }

    score = 100 * (
        W_MATCH * (match_score / 100.0) + W_FRESH * fresh + W_EASE * ease
    )
    return round(score, 1), {
        "match": match_score,
        "eligibility": eligibility,
        "freshness": round(fresh, 3),
        "ease": round(ease, 3),
        "score": round(score, 1),
        "reason": "Match dominates; freshness and application ease break ties.",
    }


def compute_bestscore(job, profile_tokens=None, eval_score=None, profile_snapshot=None):
    """Compatibility wrapper; unversioned cached eval_score is ignored."""
    from jd_analyzer import full_analyze

    analysis = full_analyze(
        job.get("title", ""),
        job.get("description", ""),
        profile_snapshot,
        job.get("location", ""),
    )
    return compute_application_priority(job, analysis)


def rank_jobs(jobs, profile_text="", eval_scores=None, profile_snapshot=None):
    """Analyze every job against one immutable snapshot and rank known scores."""
    if profile_snapshot is None:
        try:
            from profile import get_active_profile_snapshot
            profile_snapshot = get_active_profile_snapshot()
        except Exception:
            profile_snapshot = None

    from jd_analyzer import full_analyze

    ranked = []
    for job in jobs:
        analysis = full_analyze(
            job.get("title", ""),
            job.get("description", ""),
            profile_snapshot,
            job.get("location", ""),
        )
        score, breakdown = compute_application_priority(job, analysis)
        ranked.append({
            **job,
            "bestscore": score,
            "bestscore_breakdown": breakdown,
            "analysis": analysis,
            "profile_version": (profile_snapshot or {}).get("version"),
        })
    ranked.sort(
        key=lambda item: item["bestscore"] if item["bestscore"] is not None else -1,
        reverse=True,
    )
    return ranked
