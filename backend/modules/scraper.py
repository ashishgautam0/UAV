import time
import random
import re
import os
from datetime import datetime

# Internship markers — a job is REJECTED if any appear (jobs-only mode).
# "junior" / "entry level" / "graduate" / "fresher" are allowed and not listed here.
INTERN_KEYWORDS = ["intern", "internship", "trainee", "apprentice"]


def is_internship(text):
    """Check if job text contains an internship marker (intern/trainee/apprentice).
    Used to REJECT internships in jobs-only mode."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in INTERN_KEYWORDS)


_LINKEDIN_SEARCH_QUERIES = [
    "gen ai engineer",
    "generative ai engineer",
    "genai developer",
    "llm engineer",
    "ai engineer",
    "ai developer",
    "machine learning engineer",
    "ml engineer",
    "nlp engineer",
    "prompt engineer",
    "ai automation engineer",
    "deep learning engineer",
    "computer vision engineer",
    "data scientist",
    "ai research engineer",
    "research engineer ai",
    "applied scientist",
    "software development engineer",
    "software engineer ai",
    "python developer",
    "backend developer python",
    "full stack ai",
    "ai ml engineer",
    "artificial intelligence engineer",
]

_LINKEDIN_LOCATIONS = ["India", "Remote"]

_TITLE_INCLUDE = [
    "gen ai", "genai", "generative ai", "llm", "ai engineer", "ai developer",
    "nlp engineer", "machine learning engineer", "ml intern", "ai/ml",
    "ai automation", "prompt engineer", "ai research", "research intern",
    "large language model", "langchain", "rag", "agentic ai",
    "ai trainee", "deep learning", "computer vision", "data science",
]

_TITLE_REJECT = [
    "frontend", "react", "angular", "ui/ux", "devops", "cloud", "data analyst",
    "content", "marketing", "sales", "hr", "finance", "blockchain",
]

# Exact phrases score higher than partial keyword matches
_TITLE_EXACT_PHRASES = [
    "ai engineer intern", "ml engineer intern", "ai developer intern",
    "gen ai intern", "generative ai intern", "machine learning intern",
    "data science intern", "deep learning intern", "nlp intern",
    "computer vision intern", "ai research intern", "prompt engineer intern",
    "ai automation intern", "ai trainee", "llm engineer intern",
]


def _is_india_or_remote(location_str):
    """Keep job if location contains 'india' or indicates remote."""
    if not location_str or not location_str.strip():
        return False
    loc = location_str.lower()
    return "india" in loc or "remote" in loc


def _load_blacklist():
    """Load company blacklist from blacklist.txt. Returns a set of lowercase names."""
    blacklist_path = os.path.join(os.path.dirname(__file__), "..", "..", "blacklist.txt")
    try:
        with open(blacklist_path, "r", encoding="utf-8") as f:
            return {line.strip().lower() for line in f if line.strip()}
    except FileNotFoundError:
        return set()


def check_apply_type(job_url, timeout=10):
    """Best-effort check of how a LinkedIn job accepts applications.

    LinkedIn's public job page embeds <code id="applyUrl"> only when the
    posting sends applicants to an external site; Easy Apply postings have
    no such element. Returns "EASY_APPLY", "EXTERNAL", or "" when the page
    cannot be read (auth wall, rate limit, network error) so callers can
    treat it as unknown.
    """
    import requests

    try:
        resp = requests.get(
            job_url,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        if resp.status_code != 200 or not resp.text:
            return ""
        html = resp.text
        applyurl = re.search(r'id="applyUrl"[^>]*>(.*?)</code>', html, re.S)
        if applyurl and "url=" in applyurl.group(1):
            return "EXTERNAL"
        # Only trust "no applyUrl means Easy Apply" when the page actually
        # rendered job content rather than a login wall.
        if "topcard" in html or "decorated-job-posting" in html:
            return "EASY_APPLY"
        return ""
    except Exception:
        return ""


def _normalize_for_dedup(text):
    """Lowercase, strip punctuation, strip 'intern'/'internship' for dedup key."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\b(internship|intern)\b", "", text)
    return " ".join(text.split())


def _title_passes_filter(title):
    """Return True if title passes REJECT/INCLUDE filter. REJECT checked first."""
    title_lower = title.lower()
    if any(kw in title_lower for kw in _TITLE_REJECT):
        return False
    if any(kw in title_lower for kw in _TITLE_INCLUDE):
        return True
    return False



def _is_blacklisted(company, blacklist):
    """Check if company name matches any blacklisted name (substring match)."""
    if not blacklist:
        return False
    company_lower = company.lower()
    return any(bl in company_lower for bl in blacklist)



def scrape_linkedin():
    """Scrape LinkedIn via JobSpy for targeted AI/ML internships."""
    start_time = time.time()

    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("python-jobspy not installed — skipping LinkedIn scraper. Run: pip install python-jobspy")
        return []

    # Build and randomize 34 query+location combos
    combos = [(q, loc) for q in _LINKEDIN_SEARCH_QUERIES for loc in _LINKEDIN_LOCATIONS]
    random.shuffle(combos)

    blacklist = _load_blacklist()

    # Stats
    total_raw = 0
    after_location_filter = 0
    after_title_filter = 0
    after_blacklist = 0
    combos_run = 0

    # In-memory dedup: key -> job_data (with match_count)
    dedup_map = {}

    for query, location in combos:
        combos_run += 1
        try:
            results = scrape_jobs(
                site_name=["linkedin"],
                search_term=query,
                location=location,
                hours_old=24,
                results_wanted=50,
            )

            for _, row in results.iterrows():
                total_raw += 1

                title = str(row.get("title", "")).strip()
                if not title:
                    continue

                # Reject internships (jobs-only mode)
                if is_internship(title):
                    continue

                # Location filter — must contain "india"
                if not _is_india_or_remote(str(row.get("location", ""))):
                    continue
                after_location_filter += 1

                company = str(row.get("company", "Unknown")).strip() or "Unknown"
                url = str(row.get("job_url", "")).strip()

                # Blacklist check
                if _is_blacklisted(company, blacklist):
                    continue
                after_blacklist += 1

                job_location = str(row.get("location", "")).strip() or location
                desc = str(row.get("description", "") or "")[:500]
                posted_date = str(row.get("date_posted", "") or "") or None

                # In-memory dedup by normalized title + company
                dedup_key = _normalize_for_dedup(title) + "||" + _normalize_for_dedup(company)

                if dedup_key in dedup_map:
                    dedup_map[dedup_key]["match_count"] += 1
                    # Keep the URL with more info (prefer non-empty)
                    if url and not dedup_map[dedup_key]["url"]:
                        dedup_map[dedup_key]["url"] = url
                else:
                    dedup_map[dedup_key] = {
                        "title": title[:150],
                        "company": company[:80],
                        "location": job_location[:80],
                        "source": "LinkedIn",
                        "url": url,
                        "description": desc,
                        "posted_date": posted_date,
                        "source_query": query,
                        "match_count": 1,
                        "score": 0,
                        "scraped_at": datetime.now().isoformat(),
                    }

            time.sleep(3)
        except Exception as e:
            print(f"  LinkedIn query '{query}' ({location}) error: {e}")

    # Convert dedup map to list
    jobs = list(dedup_map.values())
    after_title_filter = len(jobs)

    # Print summary
    elapsed = time.time() - start_time
    avg_match = sum(j["match_count"] for j in jobs) / len(jobs) if jobs else 0
    health = "OK" if total_raw > 0 else "FAILED"

    print(f"\n--- LinkedIn Scraper Run Summary ---")
    print(f"Combinations run: {combos_run}")
    print(f"Query order: randomized")
    print(f"Time filter: last 24 hours")
    print(f"Results per query: up to 50")
    print(f"Total raw results: {total_raw}")
    print(f"After location filter: {after_location_filter} (dropped {total_raw - after_location_filter} non-India)")
    print(f"After title filter: {after_title_filter}")
    print(f"After blacklist: {after_blacklist}")
    print(f"After in-memory dedup: {len(jobs)}")
    print(f"Avg match count: {avg_match:.1f}")
    print(f"Time taken: {elapsed:.0f}s")
    print(f"Health: {health}")

    if health == "FAILED":
        print("[HEALTH CHECK FAILED] Zero raw results across all combinations — possible scraper failure.")

    return jobs



def run_all_scrapers():
    """Run the LinkedIn scraper and return results with error tracking."""
    all_jobs = []
    sources_status = {}
    sources_errors = {}

    scrapers = [
        ("LinkedIn AI/ML", scrape_linkedin),
    ]

    for name, scraper_fn in scrapers:
        print(f"Scraping {name}...")
        try:
            results = scraper_fn()
            all_jobs.extend(results)
            sources_status[name] = len(results)
            if len(results) == 0:
                print(f"  WARNING: {name} returned 0 jobs")
        except Exception as e:
            sources_status[name] = 0
            sources_errors[name] = str(e)
            print(f"  ERROR: {name} failed: {e}")

    return all_jobs, sources_status, sources_errors
