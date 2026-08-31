"""
Daily Job Search Automation
Runs the LinkedIn scraper, filters jobs, and saves them to Supabase along with
a markdown digest. Invoked once a day by a scheduled Claude routine.
"""

import os
import re
from datetime import datetime
from rapidfuzz import fuzz
from tracker import (
    init_db, save_scraped_job, save_email_log, get_existing_job_urls,
    save_notification, init_notifications_table,
)
from scraper import run_all_scrapers
from digest import build_email_content, get_alert_number


# Curated list of desired AI/ML job titles for fuzzy matching
DESIRED_TITLES = [
    "AI Engineer",
    "Generative AI Engineer",
    "Machine Learning Engineer",
    "AI/ML Developer",
    "Machine Learning Research Engineer",
    "Agentic AI Engineer",
    "Data and AI Engineer",
    "AI Agent Developer",
    "AI/ML Engineer",
    "Generative AI Developer",
    "AI Research Engineer",
    "Agentic AI Developer",
    "Deep Tech AI Engineer",
    "ML Engineer",
    "AI-ML Systems Engineer",
    "Machine Learning Scientist",
    "Artificial Intelligence Engineer",
    "LLM Engineer",
    "RAG Developer",
    "NLP Engineer",
    "LangChain Developer",
    "FastAPI Developer",
    "AI Pipeline Engineer",
    "Prompt Engineer",
    "Conversational AI Engineer",
    "AI Solutions Engineer",
    "Applied AI Engineer",
    "AI Product Engineer",
    "GenAI Engineer",
    "GenAI Researcher",
    "Generative AI Developer",
    "Deep Learning Engineer",
    "NLP Developer",
    "Document AI Engineer",
    "OCR Engineer",
    "AI Chatbot Developer",
    "MLOps Engineer",
    "AI/ML Researcher",
    "Applied Machine Learning Engineer",
    "LLM Application Developer",
    "AI Agent Engineer",
    "Predictive Modeling Engineer",
    "Multimodal AI Engineer",
    "LLM Fine-Tuning Engineer",
    "Machine Learning Developer",
    "AI ML Engineer",
    "Machine Learning Researcher",
    "ML Researcher",
    "Generative AI Developer",
    "Machine Learning Engineer",
    "AI ML Developer",
    "Speech Recognition Engineer",
    "LLM & RAG Engineer",
    "Junior Artificial Intelligence Engineer",
    "Junior ML Engineer",
    "Junior AI Engineer",
    "Entry Level AI Engineer",
    "Graduate AI Engineer",
    "Graduate ML Engineer",
    "GenAI Document AI Engineer",
    "Research Scientist",
    "Graduate Technical Engineer",
    "AI Research Scientist",
    "Python Engineer",
    "Large Language Model Engineer",
    "NLP Researcher",
    "Research Assistant AI/ML",
    "AI/ML Research and Development Engineer",
    "AI Engineer",
    "Artificial Intelligence (AI) Engineer",
    # AWS / cloud roles — Subidh holds an AWS certification (rare edge), so
    # these are first-class targets, not afterthoughts.
    "AWS Machine Learning Engineer",
    "AWS AI Engineer",
    "AWS Data Engineer",
    "Cloud Engineer",
    "AWS Cloud Engineer",
    "Cloud Data Engineer",
    "Cloud AI Engineer",
    "Cloud ML Engineer",
    "Cloud Machine Learning Engineer",
    "MLOps Engineer",
    "AWS MLOps Engineer",
    "Machine Learning Platform Engineer",
    "AI Platform Engineer",
    "ML Platform Engineer",
    "Platform Engineer",
    "AWS Solutions Architect",
    "Cloud Solutions Architect",
    "AI Solutions Architect",
    "Machine Learning Infrastructure Engineer",
    "DevOps Engineer",
    "AWS DevOps Engineer",
    "SageMaker Engineer",
    "AWS SageMaker Engineer",
    "Data Engineer",
    "AWS Data and AI Engineer",
]

# Pre-compute normalized titles for faster matching
_DESIRED_TITLES_LOWER = [t.lower().strip() for t in DESIRED_TITLES]

# Domain keywords — a job title must contain at least one to be considered relevant
_DOMAIN_KEYWORDS = {
    "ai", "ml", "artificial intelligence", "machine learning", "deep learning",
    "data science", "data scientist", "data analyst", "analytics",
    "nlp", "natural language", "computer vision", "llm", "large language model",
    "genai", "generative ai", "agentic", "rag", "langchain",
    "python", "fastapi", "backend engineer", "software engineer",
    "mlops", "prompt engineer", "chatbot", "conversational ai",
    "iot", "robotics", "uav", "digital twin", "edge computing", "simulation",
    "ocr", "document ai", "speech recognition", "predictive modeling",
    "optimization algorithm", "multimodal",
    # AWS / cloud vocabulary — Subidh's AWS certification is the edge we're
    # leaning into, so cloud roles must clear the coarse title gate and reach
    # Claude's resume-screener rather than being pre-rejected here.
    "aws", "amazon web services", "cloud", "sagemaker", "bedrock",
    "solutions architect", "cloud architect", "data engineer",
    "platform engineer", "devops", "mlops", "sre", "site reliability",
    "kubernetes", "terraform", "infrastructure",
}


# Internship markers — any title containing these is rejected (jobs-only mode)
_INTERN_REJECT_KEYWORDS = ("intern", "internship", "trainee", "apprentice")

# Titles matching any of these (case-insensitive, word-boundary) are rejected:
# senior/staff/principal/lead levels, Java roles, generic Software Engineer /
# Data Scientist roles, and mid-level postings.
_TITLE_REJECT_RE = re.compile(
    r"\b("
    r"senior|sr|staff|principal|lead|phd|distinguished|"
    r"java|"
    r"software engineer|data scientist|data science|backend engineer|specialist|"
    r"python developer|python automation engineer|manager|computer vision|"
    r"mid[\s-]?level"
    r")\b",
    re.IGNORECASE,
)


def _matches_desired_title(job_title, threshold=60):
    """Check if a job title matches any desired title.

    Filter pipeline (jobs-only, junior/entry only):
    1. Reject titles containing an internship marker.
    2. Reject senior/staff/principal/lead/PhD, Java, Software Engineer,
       Data Scientist, Backend Engineer, Specialist, and mid-level titles
       (see _TITLE_REJECT_RE).
    3. Reject generic one-word titles.
    4. Exact match against the curated list (normalized).
    5. Domain keyword check + fuzzy match — the title must contain a relevant
       domain keyword AND score >= threshold via token_sort_ratio against at
       least one desired title. This prevents false positives like
       'Market Research Engineer' matching 'Research Engineer'.
    """
    normalized = job_title.lower().strip()
    if not normalized:
        return False

    # Step 1: reject internships
    if any(kw in normalized for kw in _INTERN_REJECT_KEYWORDS):
        return False

    # Step 2: reject senior/staff/principal/lead, Java, generic SWE/DS, mid-level
    if _TITLE_REJECT_RE.search(normalized):
        return False

    # Step 3: reject generic one-word titles
    if normalized in ("engineer", "developer", "scientist", "analyst"):
        return False

    # Step 3: exact match
    if normalized in _DESIRED_TITLES_LOWER:
        return True

    # Step 4: must contain at least one domain keyword
    has_domain_keyword = any(kw in normalized for kw in _DOMAIN_KEYWORDS)
    if not has_domain_keyword:
        return False

    # Step 5: fuzzy match using token_set_ratio. Unlike token_sort_ratio it
    # ignores trailing/extra qualifier words, so real roles like "Machine
    # Learning Engineer, Amazon Music - Catalog Quality" or "AI Engineer - FDE
    # (Forward Deployed Engineer)" match their base title instead of being
    # penalized to death by the extra words. The domain-keyword gate above still
    # blocks off-domain noise, and Claude's resume-screener is the real filter.
    best = max(
        fuzz.token_set_ratio(normalized, desired)
        for desired in _DESIRED_TITLES_LOWER
    )
    return best >= threshold


# Entry-level signals: if the JD says any of these, it is treating the role as
# 0-1 years / fresher, so keep it regardless of any other number it mentions.
_ENTRY_SIGNAL_RE = re.compile(
    r"(0\s*[-–to]{1,3}\s*1\s*years?|0\s*[-–to]{1,3}\s*2\s*years?|"
    r"fresher|entry[\s-]?level|new\s*grad|recent\s+graduate|"
    r"up\s+to\s+1\s+year|less\s+than\s+(?:1|one)\s+year|no\s+experience|"
    r"\b1\s*\+?\s*years?\b)",
    re.IGNORECASE,
)
# Any experience phrase whose LOWER bound is a number — used to read the minimum
# years a JD asks for. Matches "5 years", "3-5 years", "6-8 years", "2+ years",
# "3 to 5 years" and (with backslashes stripped first) markdown-escaped forms
# like "6\-8 years".
_YEARS_PHRASE_RE = re.compile(r"(\d+)\s*(?:[-–+]|to)?\s*\d*\s*\+?\s*years?", re.IGNORECASE)


def _experience_ok(description):
    """Coarse 0-1-years pre-net on the JD text.

    Keeps a job when its stated experience requirement is entry-level (0-1
    years / fresher) OR no years are stated at all; drops a job whose minimum
    stated experience is 2+ years. Claude's resume-screener makes the final call.

    JD text scraped from LinkedIn/Indeed is markdown, so hyphens arrive escaped
    ("6\\-8 years"); strip backslashes before matching so ranges are read.
    """
    text = (description or "").replace("\\", "")
    if _ENTRY_SIGNAL_RE.search(text):
        return True
    # Drop if any experience phrase's lower bound is >= 2 years.
    for m in _YEARS_PHRASE_RE.finditer(text):
        try:
            if int(m.group(1)) >= 2:
                return False
        except (ValueError, TypeError):
            continue
    return True  # no explicit years stated — let Claude decide


def _resume_fit_filter(jobs):
    """Coarse resume pre-net — NOT the real decision.

    This only drops jobs that share almost nothing with the resume, purely to
    cap volume before the routine's resume-screener agent (Claude) makes the
    real fit + experience-level decision on each survivor. Keep the bar low
    (RESUME_MIN_SKILL_HITS, default 2) so Claude — not keywords — decides.
    If no real resume is stored yet, the net is skipped so nothing is lost.
    """
    try:
        from ranking import _tokens
        from message_generator import _get_profile_text
    except Exception:
        return jobs, "skipped (ranking/profile unavailable)"

    resume = (_get_profile_text() or "").strip()
    if len(resume) < 120:
        return jobs, "skipped (no resume uploaded yet)"

    resume_tokens = _tokens(resume)
    if len(resume_tokens) < 8:
        return jobs, "skipped (resume too thin to match on)"

    try:
        min_hits = int(os.environ.get("RESUME_MIN_SKILL_HITS", "2"))
    except ValueError:
        min_hits = 2

    kept = []
    thin_kept = 0
    for j in jobs:
        desc = j.get("description", "") or ""
        jd = _tokens(f"{j.get('title', '')} {desc}")
        hits = len(resume_tokens & jd)
        # A short JD snippet (e.g. amazon.jobs' ~200-char teaser) can't be judged
        # fairly on token overlap — keep it and let Claude's resume-screener read
        # the full posting. The job already cleared the desired-title gate, so it
        # is on-domain. Only rich descriptions face the >= min_hits bar.
        if hits >= min_hits or len(desc) < 400:
            j["resume_hits"] = hits
            kept.append(j)
            if hits < min_hits:
                thin_kept += 1
    note = f"kept {len(kept)}/{len(jobs)} (>= {min_hits} hits)"
    if thin_kept:
        note += f", {thin_kept} thin-JD kept for Claude"
    return kept, note


def main():
    print("=== Hourly Job Search Automation ===")
    print(f"Running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize database
    init_db()
    init_notifications_table()

    # Run all automated scrapers
    print("Running scrapers...")
    jobs, sources_status, sources_errors = run_all_scrapers()
    print(f"\nTotal jobs found: {len(jobs)}")
    for source, count in sources_status.items():
        print(f"  {source}: {count}")
    if sources_errors:
        print(f"\nFailed scrapers: {', '.join(sources_errors.keys())}")

    # Filter out already-seen jobs (deduplication across hourly runs). Bounded
    # to a recent window so the all-time table (thousands of old/dismissed rows)
    # doesn't block genuinely re-listed roles. Tunable via DEDUP_WINDOW_DAYS.
    print("\nChecking for duplicates...")
    try:
        dedup_days = int(os.environ.get("DEDUP_WINDOW_DAYS", "14"))
    except ValueError:
        dedup_days = 14
    existing_urls = get_existing_job_urls(since_days=dedup_days)
    new_jobs = [j for j in jobs if j.get("url", "") not in existing_urls]
    print(f"New jobs: {len(new_jobs)} (filtered out {len(jobs) - len(new_jobs)} duplicates)")

    # Only keep jobs whose title matches or is similar to the desired titles list
    new_jobs = [j for j in new_jobs if _matches_desired_title(j.get("title", ""))]
    print(f"After title filter (desired titles match): {len(new_jobs)}")

    # Keep only entry-level roles: JD requires 0-1 years (or states no years).
    # Drops anything clearly asking for 2+ years before Claude screens.
    before_exp = len(new_jobs)
    new_jobs = [j for j in new_jobs if _experience_ok(j.get("description", ""))]
    print(f"After experience filter (0-1 yrs): {len(new_jobs)} "
          f"(dropped {before_exp - len(new_jobs)} needing 2+ yrs)")

    # Coarse resume pre-net (the routine's resume-screener agent is the real
    # fit + experience-level decision — Claude, not keywords).
    new_jobs, resume_note = _resume_fit_filter(new_jobs)
    print(f"After resume pre-net: {resume_note}")

    # Health check: if LinkedIn scraper returned 0 results, flag it
    linkedin_count = sources_status.get("LinkedIn AI/ML", 0)
    if linkedin_count == 0 and "LinkedIn AI/ML" not in sources_errors:
        print("\n[HEALTH CHECK FAILED] LinkedIn scraper returned 0 results — possible scraper failure.")
        try:
            save_notification(
                title="Scraper Health Check Failed",
                body="LinkedIn AI/ML scraper returned 0 results. Possible scraper failure — check logs.",
                notification_type="health_check",
                metadata={"source": "LinkedIn AI/ML", "timestamp": datetime.now().isoformat()},
            )
        except Exception:
            pass

    # Auto-analyze top jobs for verdict/ATS
    if new_jobs:
        print("\nRunning auto-analysis on top jobs...")
        try:
            from jd_analyzer import full_analyze, quick_ats
            for job in new_jobs[:15]:
                try:
                    result = full_analyze(job.get("title", ""), job.get("description", ""))
                    job["ats_score"] = quick_ats(job.get("description", ""))
                    job["skill_match"] = result.get("skills", {}).get("match_percentage", 0)
                    job["noc_verdict"] = result.get("noc", {}).get("confidence", "")
                except Exception:
                    pass
            print(f"Auto-analysis complete for top {min(15, len(new_jobs))} jobs.")
        except ImportError:
            print("jd_analyzer not available — skipping auto-analysis.")

    # Easy Apply availability, stored in the verdict column. Only the new
    # jobs are checked (one page fetch each) to stay under LinkedIn's radar.
    if new_jobs:
        print("\nChecking Easy Apply availability...")
        import time as _time
        from scraper import check_apply_type
        for job in new_jobs:
            job["verdict"] = check_apply_type(job.get("url", ""))
            _time.sleep(1)
        known = sum(1 for j in new_jobs if j.get("verdict"))
        print(f"Apply type known for {known}/{len(new_jobs)} new jobs.")

    # Save new jobs to database
    print("\nSaving new jobs to database...")
    for job in new_jobs:
        try:
            save_scraped_job(
                title=job.get("title", ""),
                company=job.get("company", ""),
                location=job.get("location", ""),
                source=job.get("source", ""),
                url=job.get("url", ""),
                description=job.get("description", ""),
                score=job.get("score", 0),
                verdict=job.get("verdict", ""),
                ats_score=job.get("ats_score", 0),
            )
        except Exception:
            pass

    # Nothing to record if there are no new jobs
    if not new_jobs:
        print("\nNo new jobs found this run.")
        print("Done!")
        return

    print("\nBuilding digest...")
    alert_number = get_alert_number()

    for job in new_jobs:
        job["filtered"] = True

    md_content = build_email_content(new_jobs, sources_status, sources_errors)

    # Save to Supabase so the frontend can display it
    print("Saving digest to database...")
    try:
        save_email_log(
            subject=f"Job Alert #{alert_number}",
            markdown_content=md_content,
            html_content="",
            jobs_count=len(new_jobs),
            sources_summary=sources_status,
        )
    except Exception as e:
        print(f"  WARNING: Could not save digest to database: {e}")

    # Save in-app notification
    print("Saving in-app notification...")
    try:
        save_notification(
            title=f"Job Alert #{alert_number}",
            body=f"{len(new_jobs)} new jobs found",
            notification_type="job_alert",
            metadata={
                "jobs_count": len(new_jobs),
                "alert_number": alert_number,
                "sources": sources_status,
            },
        )
    except Exception as e:
        print(f"  WARNING: Could not save notification: {e}")

    print(f"\nDone! Job Alert #{alert_number}: {len(new_jobs)} jobs saved.")


if __name__ == "__main__":
    main()
