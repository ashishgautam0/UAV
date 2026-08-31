"""BestScore — rank scraped jobs so the best India roles float to the top.

"Best" here is a composite that answers one question: which jobs should
Subidh apply to first, right now? It blends

  * FIT        how well the JD matches his profile — the A–H evaluation's
               1–5 fit score when the research agent has scored the job,
               otherwise a lexical profile↔JD overlap fallback.
  * FRESHNESS  how recently the job was scraped — a proxy for "few applicants
               so far", since the scraper only pulls the last ~24h. Early
               applicants win, so newer ranks higher.
  * EASE       Easy Apply postings can be applied to in seconds, so they get a
               small nudge (speed, not quality).

Everything is computed live from the columns already in `scraped_jobs` plus the
cached A–H evaluation — no schema change and no external calls.
"""

import re
from datetime import datetime, timezone

# Weights sum to 1.0; FIT dominates because "best" is about match, not speed.
# AWS gets its own weight: Subidh holds an AWS certification that few
# candidates have, so a job that wants AWS/cloud (especially a certification)
# is a rare-advantage role and should rank higher.
W_FIT = 0.46
W_FRESH = 0.15
W_EASE = 0.06
W_AWS = 0.22
W_DEGREE = 0.11

# Detect AWS / cloud-certification relevance in a JD.
_AWS_CERT_RE = re.compile(
    r"aws\s+certif|certified\s+.*aws|cloud\s+certif|"
    r"solutions?\s+architect\s+cert",
    re.IGNORECASE,
)
_AWS_RE = re.compile(
    r"\b(aws|amazon web services|sagemaker|bedrock|ec2|s3|lambda|"
    r"cloudformation|eks|ecs)\b",
    re.IGNORECASE,
)

# Detect an advanced-degree preference in a JD. Subidh holds an M.Tech in AI,
# so a role that wants a master's (or advanced degree) is one where that degree
# is a real differentiator — surface it higher.
_DEGREE_RE = re.compile(
    r"master'?s?\s+degree|master\s+of|\bm\.?s\.?\b|\bm\.?sc\b|\bm\.?tech\b|"
    r"\bms\s*/\s*phd\b|\bphd\b|doctoral|postgraduate|graduate\s+degree|"
    r"advanced\s+degree",
    re.IGNORECASE,
)


def _aws_signal(job):
    """1.0 when the JD wants an AWS/cloud certification, 0.6 when it just uses
    AWS, 0 otherwise — so cert-required roles rank highest."""
    text = f"{job.get('title', '')} {job.get('description', '')}"
    if _AWS_CERT_RE.search(text):
        return 1.0
    if _AWS_RE.search(text):
        return 0.6
    return 0.0


def _degree_signal(job):
    """1.0 when the JD wants a master's / advanced degree (Subidh's M.Tech in AI
    is a differentiator there), 0 otherwise."""
    text = f"{job.get('title', '')} {job.get('description', '')}"
    return 1.0 if _DEGREE_RE.search(text) else 0.0

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
        t for t in re.split(r"[^a-z0-9+#.]+", (text or "").lower())
        if len(t) > 2 and t not in _STOP
    }


def _fit_from_lexical(profile_tokens, jd_text, title):
    """Fallback fit when there is no A–H evaluation yet.

    Rewards a JD that hits many of the candidate's own skill tokens, with a
    small bonus when profile terms appear in the title (a strong signal).
    Returns 0..1.
    """
    if not profile_tokens:
        return 0.0
    jd = _tokens(jd_text)
    if not jd:
        return 0.0
    overlap = profile_tokens & jd
    # Normalise by a realistic ceiling of matched skills (~12), not the whole
    # profile, so a well-matched JD can reach ~1.0.
    base = min(len(overlap) / 12.0, 1.0)
    title_hits = len(profile_tokens & _tokens(title))
    bonus = min(title_hits * 0.08, 0.24)
    return min(base + bonus, 1.0)


def _freshness(scraped_at):
    """1.0 for a just-scraped job, decaying to a 0.2 floor by ~48h."""
    if not scraped_at:
        return 0.5
    try:
        dt = datetime.fromisoformat(str(scraped_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.5
    hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    return max(0.2, min(1.0, 1.0 - hours / 48.0))


def compute_bestscore(job, profile_tokens, eval_score=None):
    """Return (score_0_100, breakdown) for one scraped-job dict.

    eval_score is the A–H fit score (1..5) when available; when it is, it is the
    authoritative fit signal and the lexical fallback is skipped.
    """
    if eval_score is not None:
        try:
            fit = max(0.0, min(1.0, float(eval_score) / 5.0))
            fit_src = "A–H evaluation"
        except (ValueError, TypeError):
            eval_score = None
    if eval_score is None:
        fit = _fit_from_lexical(
            profile_tokens, job.get("description", ""), job.get("title", "")
        )
        fit_src = "profile↔JD match"

    fresh = _freshness(job.get("scraped_at"))
    ease = 1.0 if (job.get("verdict") == "EASY_APPLY") else 0.55
    aws = _aws_signal(job)
    degree = _degree_signal(job)

    score = 100.0 * (
        W_FIT * fit + W_FRESH * fresh + W_EASE * ease
        + W_AWS * aws + W_DEGREE * degree
    )
    breakdown = {
        "fit": round(fit, 3),
        "fit_source": fit_src,
        "freshness": round(fresh, 3),
        "ease": round(ease, 3),
        "aws": round(aws, 3),
        "degree": round(degree, 3),
        "score": round(score, 1),
    }
    return round(score, 1), breakdown


def rank_jobs(jobs, profile_text="", eval_scores=None):
    """Attach bestscore + breakdown to each job dict and return them sorted
    high→low. `eval_scores` maps job id -> A–H fit score (1..5)."""
    profile_tokens = _tokens(profile_text)
    eval_scores = eval_scores or {}
    ranked = []
    for job in jobs:
        score, breakdown = compute_bestscore(
            job, profile_tokens, eval_scores.get(job.get("id"))
        )
        job = {**job, "bestscore": score, "bestscore_breakdown": breakdown}
        ranked.append(job)
    ranked.sort(key=lambda j: j["bestscore"], reverse=True)
    return ranked
