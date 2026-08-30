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
    # AWS-focused — Subidh is AWS certified (rare), so prioritise roles that
    # want AWS/cloud skills where that certification is a real differentiator.
    "aws machine learning engineer",
    "aws ai engineer",
    "aws generative ai engineer",
    "mlops engineer aws",
    "sagemaker engineer",
    "aws ml engineer",
    "cloud machine learning engineer",
    "cloud ai engineer",
    "machine learning engineer aws certified",
    "ai engineer cloud",
]

# Focused query set for the additional boards (Naukri / Indeed / Google Jobs):
# AWS-first, then the core field, to keep per-board runtime bounded.
_BOARD_SEARCH_QUERIES = [
    "aws machine learning engineer",
    "aws ai engineer",
    "mlops engineer aws",
    "aws generative ai",
    "cloud ai engineer",
    "machine learning engineer",
    "ai engineer",
    "generative ai engineer",
]

_LINKEDIN_LOCATIONS = ["India", "Remote"]

_TITLE_INCLUDE = [
    "gen ai", "genai", "generative ai", "llm", "ai engineer", "ai developer",
    "nlp engineer", "machine learning engineer", "ml intern", "ai/ml",
    "ai automation", "prompt engineer", "ai research", "research intern",
    "large language model", "langchain", "rag", "agentic ai",
    "ai trainee", "deep learning", "computer vision", "data science",
    "aws", "mlops", "cloud ai", "cloud ml", "sagemaker",
]

# "cloud" removed from rejects: AWS/cloud AI roles are now a priority target.
_TITLE_REJECT = [
    "frontend", "react", "angular", "ui/ux", "devops", "data analyst",
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
        # LinkedIn's guest job page tags its Apply button with exactly one of
        # these tracking markers: "offsite" postings hand applicants to an
        # external site, "onsite" ones are Easy Apply. Require a positive
        # marker for either answer — never guess from absence.
        if "apply-link-offsite" in html or "offsite-apply-icon" in html:
            return "EXTERNAL"
        if "apply-link-onsite" in html or "onsite-apply-icon" in html:
            return "EASY_APPLY"
        applyurl = re.search(r'id="applyUrl"[^>]*>(.*?)</code>', html, re.S)
        if applyurl and "url=" in applyurl.group(1):
            return "EXTERNAL"
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



# ---------------------------------------------------------------------------
# Additional boards — all-in on AWS/cloud roles that fit the field.
# ---------------------------------------------------------------------------

def _scrape_jobspy_board(site, label, country_indeed=None):
    """Generic JobSpy scraper for an extra board (Naukri / Indeed / Google).

    AWS-first query set, India + Remote, recent postings, with the same title/
    location/blacklist filters and in-memory dedup as LinkedIn.
    """
    try:
        from jobspy import scrape_jobs
    except ImportError:
        return []

    blacklist = _load_blacklist()
    dedup_map = {}
    combos = [(q, loc) for q in _BOARD_SEARCH_QUERIES for loc in _LINKEDIN_LOCATIONS]
    random.shuffle(combos)

    for query, location in combos:
        try:
            kwargs = dict(
                site_name=[site],
                search_term=query,
                location=location,
                results_wanted=40,
                hours_old=48,
            )
            if country_indeed:
                kwargs["country_indeed"] = country_indeed
            if site == "google":
                kwargs["google_search_term"] = f"{query} jobs in India since yesterday"
            results = scrape_jobs(**kwargs)

            for _, row in results.iterrows():
                title = str(row.get("title", "")).strip()
                if not title or is_internship(title):
                    continue
                if not _title_passes_filter(title):
                    continue
                loc_str = str(row.get("location", "")).strip()
                if site == "google" and not _is_india_or_remote(loc_str):
                    continue
                company = str(row.get("company", "Unknown")).strip() or "Unknown"
                if _is_blacklisted(company, blacklist):
                    continue
                url = str(row.get("job_url", "")).strip()
                desc = str(row.get("description", "") or "")[:500]
                key = _normalize_for_dedup(title) + "||" + _normalize_for_dedup(company)
                if key in dedup_map:
                    dedup_map[key]["match_count"] += 1
                    if url and not dedup_map[key]["url"]:
                        dedup_map[key]["url"] = url
                else:
                    dedup_map[key] = {
                        "title": title[:150],
                        "company": company[:80],
                        "location": (loc_str or location)[:80],
                        "source": label,
                        "url": url,
                        "description": desc,
                        "posted_date": str(row.get("date_posted", "") or "") or None,
                        "source_query": query,
                        "match_count": 1,
                        "score": 0,
                        "scraped_at": datetime.now().isoformat(),
                    }
            time.sleep(3)
        except Exception as e:
            print(f"  {label} query '{query}' ({location}) error: {e}")

    jobs = list(dedup_map.values())
    print(f"--- {label}: {len(jobs)} jobs after filter+dedup ---")
    return jobs


def scrape_naukri():
    """Naukri — India's largest board; JDs name AWS/cloud/certs explicitly."""
    return _scrape_jobspy_board("naukri", "Naukri")


def scrape_indeed_india():
    """Indeed India — high volume, cert/skill-rich JDs, scrape-friendly."""
    return _scrape_jobspy_board("indeed", "Indeed", country_indeed="India")


def scrape_google_jobs():
    """Google Jobs aggregator — pulls cert-mentioning postings web-wide."""
    return _scrape_jobspy_board("google", "Google Jobs")


def scrape_amazon_jobs():
    """AWS's own careers (amazon.jobs) via its public search.json — the source
    most likely to want AWS. India + AWS/ML/AI queries."""
    import requests

    queries = ["machine learning", "generative ai", "applied scientist",
               "ai engineer", "mlops"]
    dedup_map = {}
    for q in queries:
        try:
            resp = requests.get(
                "https://www.amazon.jobs/en/search.json",
                params={"result_limit": 50, "offset": 0, "base_query": q,
                        "loc_query": "India", "country": "IND", "sort": "recent"},
                headers={"User-Agent": "Mozilla/5.0"}, timeout=15,
            )
            data = resp.json()
        except Exception as e:
            print(f"  amazon.jobs query '{q}' error: {e}")
            continue
        for row in data.get("jobs", []) or []:
            title = (row.get("title") or "").strip()
            if not title or is_internship(title) or not _title_passes_filter(title):
                continue
            path = row.get("job_path") or ""
            url = f"https://www.amazon.jobs{path}" if path else ""
            # Prefer the full description over the short teaser so downstream
            # resume-screening / drafting agents (and the resume pre-net) have
            # real JD content to judge, not a 200-char snippet.
            raw_desc = " ".join(filter(None, [
                row.get("description") or "",
                row.get("basic_qualifications") or "",
                row.get("preferred_qualifications") or "",
            ])) or (row.get("description_short") or "")
            desc = re.sub(r"<[^>]+>", " ", raw_desc)
            desc = re.sub(r"\s+", " ", desc)[:2000]
            key = _normalize_for_dedup(title) + "||amazon"
            if key not in dedup_map:
                dedup_map[key] = {
                    "title": title[:150], "company": "Amazon (AWS)",
                    "location": (row.get("normalized_location") or "India")[:80],
                    "source": "amazon.jobs", "url": url, "description": desc.strip(),
                    "posted_date": row.get("posted_date"), "source_query": q,
                    "match_count": 1, "score": 0,
                    "scraped_at": datetime.now().isoformat(),
                }
        time.sleep(1)
    jobs = list(dedup_map.values())
    print(f"--- amazon.jobs: {len(jobs)} jobs after filter+dedup ---")
    return jobs


# AWS-partner / cloud-heavy employers with public ATS feeds (verified reachable).
_GREENHOUSE_BOARDS = ["databricks", "mongodb", "elastic", "fivetran", "druva", "groww", "postman"]
_LEVER_BOARDS = ["cred", "meesho", "mindtickle"]


def scrape_partner_ats():
    """AWS-partner / cloud-heavy companies via public Greenhouse + Lever APIs.
    India-located field roles only. Official JSON feeds, not scraping."""
    import requests

    dedup_map = {}

    def _add(title, company, url, desc, loc):
        if not title or is_internship(title) or not _title_passes_filter(title):
            return
        if not _is_india_or_remote(loc):
            return
        key = _normalize_for_dedup(title) + "||" + _normalize_for_dedup(company)
        if key not in dedup_map:
            dedup_map[key] = {
                "title": title[:150], "company": company[:80],
                "location": (loc or "India")[:80], "source": "Partner ATS",
                "url": url, "description": re.sub(r"<[^>]+>", " ", desc or "")[:500].strip(),
                "posted_date": None, "source_query": "partner-ats",
                "match_count": 1, "score": 0,
                "scraped_at": datetime.now().isoformat(),
            }

    for board in _GREENHOUSE_BOARDS:
        try:
            r = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs",
                params={"content": "true"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            for j in (r.json().get("jobs", []) or []):
                _add(j.get("title", ""), board.capitalize(),
                     j.get("absolute_url", ""), j.get("content", ""),
                     (j.get("location") or {}).get("name", ""))
        except Exception as e:
            print(f"  greenhouse '{board}' error: {e}")
        time.sleep(0.5)

    for board in _LEVER_BOARDS:
        try:
            r = requests.get(f"https://api.lever.co/v0/postings/{board}",
                             params={"mode": "json"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            for j in (r.json() or []):
                cats = j.get("categories") or {}
                _add(j.get("text", ""), board.capitalize(), j.get("hostedUrl", ""),
                     j.get("descriptionPlain", ""), cats.get("location", ""))
        except Exception as e:
            print(f"  lever '{board}' error: {e}")
        time.sleep(0.5)

    jobs = list(dedup_map.values())
    print(f"--- Partner ATS: {len(jobs)} jobs after filter+dedup ---")
    return jobs


def run_all_scrapers():
    """Run all scrapers (LinkedIn + AWS-focused boards) with error tracking."""
    all_jobs = []
    sources_status = {}
    sources_errors = {}

    scrapers = [
        ("LinkedIn AI/ML", scrape_linkedin),
        ("Naukri", scrape_naukri),
        ("Indeed India", scrape_indeed_india),
        ("Google Jobs", scrape_google_jobs),
        ("amazon.jobs", scrape_amazon_jobs),
        ("Partner ATS", scrape_partner_ats),
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
