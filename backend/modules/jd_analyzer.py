"""
JD Analyzer — NOC compatibility check, skill match scoring, red flag detection,
ATS resume compatibility check.
Used both in the Streamlit UI (full analysis) and in hourly.py (quick verdict).
"""

import re

from resume_profile import SKILL_ALIASES, extract_profile_facts, phrase_present


ANALYSIS_VERSION = "explainable-match-v1"

# --- NOC Codes relevant to tech roles ---
NOC_CODES = {
    "21232": {
        "title": "Software Developers and Programmers",
        "duties": [
            "design, develop, test", "write code", "software applications",
            "maintain software", "programming", "web applications",
            "develop software", "build applications", "implement features",
        ],
    },
    "21211": {
        "title": "Data Scientists",
        "duties": [
            "machine learning", "data analysis", "statistical models",
            "algorithms", "data mining", "predictive models",
            "deep learning", "neural network", "data pipeline",
        ],
    },
    "21231": {
        "title": "Software Engineers",
        "duties": [
            "software architecture", "system design", "software requirements",
            "technical leadership", "software systems", "scalable systems",
            "microservices", "distributed systems",
        ],
    },
    "21222": {
        "title": "Information Systems Specialists",
        "duties": [
            "information systems", "system administration", "IT infrastructure",
            "technical support", "system analysis", "database administration",
        ],
    },
    "21234": {
        "title": "Web Developers and Programmers",
        "duties": [
            "web application", "frontend", "backend", "full stack",
            "website development", "web services", "rest api", "api development",
        ],
    },
    "21230": {
        "title": "Computer Systems Developers and Programmers (General)",
        "duties": [
            "develop software", "programming", "coding", "technical solutions",
            "application development", "software development",
        ],
    },
}

# --- ATS Synonym Groups ---
SYNONYM_GROUPS = [
    {"js", "javascript", "ecmascript"},
    {"ts", "typescript"},
    {"node", "node.js", "nodejs"},
    {"react", "react.js", "reactjs"},
    {"next", "next.js", "nextjs"},
    {"vue", "vue.js", "vuejs"},
    {"express", "express.js", "expressjs"},
    {"fastapi", "fast api"},
    {"scikit-learn", "sklearn", "scikit learn"},
    {"langchain", "lang chain"},
    {"langgraph", "lang graph"},
    {"hugging face", "huggingface", "hf"},
    {"ml", "machine learning"},
    {"dl", "deep learning"},
    {"nlp", "natural language processing"},
    {"cv", "computer vision"},
    {"gen ai", "generative ai", "genai"},
    {"llm", "large language model", "large language models"},
    {"rag", "retrieval augmented generation", "retrieval-augmented generation"},
    {"ai agent", "agentic ai", "agentic"},
    {"k8s", "kubernetes"},
    {"aws", "amazon web services"},
    {"gcp", "google cloud", "google cloud platform"},
    {"azure", "microsoft azure"},
    {"ci/cd", "cicd", "ci cd", "continuous integration"},
    {"terraform", "tf", "infrastructure as code"},
    {"postgres", "postgresql"},
    {"mongo", "mongodb"},
    {"chromadb", "chroma", "chroma db"},
    {"elastic", "elasticsearch", "elastic search"},
    {"rabbitmq", "rabbit mq"},
    {"golang", "go lang"},
    {"c#", "csharp", "c sharp"},
    {"c++", "cpp"},
    {"rest api", "restful api", "rest apis", "restful"},
    {"graphql", "graph ql"},
    {"docker", "containerization", "containers"},
    {"git", "version control"},
    {"sql", "structured query language"},
    {"html", "html5"},
    {"css", "css3"},
    {"tailwind", "tailwind css", "tailwindcss"},
    {"sass", "scss"},
    {"selenium", "web automation"},
    {"etl", "extract transform load"},
    {"airflow", "apache airflow"},
    {"spark", "apache spark", "pyspark"},
    {"kafka", "apache kafka"},
    {"pinecone", "pinecone db"},
    {"weaviate", "weaviate db"},
    {"cohere", "cohere api"},
    {"openai", "openai api"},
]

_SYNONYM_LOOKUP = {}
for _group in SYNONYM_GROUPS:
    _frozen = frozenset(_group)
    for _term in _group:
        _SYNONYM_LOOKUP[_term] = _frozen


def _expand_synonyms(term):
    """Return all known synonyms for a term, including itself."""
    return _SYNONYM_LOOKUP.get(term.lower(), frozenset({term.lower()}))


# --- ATS Requirement Extraction Patterns ---
_EXPERIENCE_PATTERNS = [
    re.compile(
        r"(?:minimum|at\s+least|min\.?)?\s*(\d+)\s*(?:\+|[-–—]\s*\d+|to\s+\d+)?\s*years?\s+"
        r"(?:of\s+)?(?:experience|exp\.?|work\s+experience)",
        re.IGNORECASE,
    ),
    re.compile(r"(\d+)\s*\+?\s*yrs?\s+(?:of\s+)?(?:experience|exp\.?)", re.IGNORECASE),
]

_DEGREE_PATTERNS = [
    re.compile(
        r"(?<!\w)(?:bachelor'?s?|b\.?s\.?|b\.?tech|b\.?e\.?)"
        r"(?:\s+degree)?(?:\s+in)?(?!\w)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<!\w)(?:master'?s?|m\.?s\.?|m\.?tech|m\.?e\.?)"
        r"(?:\s+degree)?(?:\s+in)?(?!\w)",
        re.IGNORECASE,
    ),
    re.compile(r"(?<!\w)(?:ph\.?d\.?|doctorate)(?!\w)", re.IGNORECASE),
]

_CERT_PATTERNS = [
    re.compile(
        r"(AWS\s+(?:Solutions?\s+Architect|Developer|SysOps|DevOps)|"
        r"Azure\s+(?:Developer|Administrator|AI\s+Engineer)|"
        r"GCP\s+(?:Professional|Associate)|"
        r"PMP|Scrum\s+Master|CISSP|CKA|CKAD)",
        re.IGNORECASE,
    ),
]


def _extract_experience_requirement(text):
    results = []
    seen = set()
    for pattern in _EXPERIENCE_PATTERNS:
        for match in pattern.finditer(text):
            years = int(match.group(1))
            context = text[max(0, match.start() - 80):min(len(text), match.end() + 80)]
            preferred = bool(re.search(r"preferred|nice\s+to\s+have|desirable|plus", context, re.I))
            key = (years, preferred)
            if key not in seen:
                seen.add(key)
                results.append({
                    "type": "experience", "value": match.group(0).strip(),
                    "years": years, "required": not preferred,
                })
    return results


def _extract_degree_requirements(text):
    results = []
    seen = set()
    level_order = {"bachelor": 2, "master": 3, "doctorate": 4}
    alternative_spans = []
    alt_pattern = re.compile(
        r"(?P<left>bachelor'?s?|b\.?s\.?|b\.?tech|master'?s?|m\.?s\.?|m\.?tech)"
        r"(?:\s+degree)?\s*(?:/|or)\s*"
        r"(?P<right>master'?s?|m\.?s\.?|m\.?tech|ph\.?d\.?|doctorate)",
        re.IGNORECASE,
    )

    def level_for(raw):
        lowered = raw.lower()
        return ("doctorate" if re.search(r"ph|doctor", lowered) else
                "master" if re.search(r"master|m\.?s|m\.?tech|m\.?e", lowered) else
                "bachelor")

    for match in alt_pattern.finditer(text):
        levels = [level_for(match.group("left")), level_for(match.group("right"))]
        minimum = min(levels, key=level_order.get)
        context = text[max(0, match.start() - 100):min(len(text), match.end() + 100)]
        preferred = bool(re.search(r"preferred|nice\s+to\s+have|desirable|plus", context, re.I))
        results.append({
            "type": "degree", "value": match.group(0).strip(), "level": minimum,
            "required": not preferred, "alternatives": levels,
        })
        seen.add((minimum, preferred))
        alternative_spans.append(match.span())

    for pattern in _DEGREE_PATTERNS:
        for match in pattern.finditer(text):
            if any(left <= match.start() < right for left, right in alternative_spans):
                continue
            raw = match.group(0).strip()
            level = level_for(raw)
            context = text[max(0, match.start() - 100):min(len(text), match.end() + 100)]
            preferred = bool(re.search(r"preferred|nice\s+to\s+have|desirable|plus", context, re.I))
            key = (level, preferred)
            if key not in seen:
                seen.add(key)
                results.append({
                    "type": "degree", "value": raw, "level": level,
                    "required": not preferred,
                })
    return results


def _extract_cert_requirements(text):
    results = []
    for pattern in _CERT_PATTERNS:
        for match in pattern.finditer(text):
            context = text[max(0, match.start() - 100):min(len(text), match.end() + 100)]
            preferred = bool(re.search(r"preferred|nice\s+to\s+have|desirable|plus", context, re.I))
            results.append({
                "type": "certification", "value": match.group(0).strip(),
                "required": not preferred,
            })
    return results


def _profile_facts(profile_snapshot):
    if not profile_snapshot:
        return {}
    if profile_snapshot.get("facts"):
        return profile_snapshot["facts"]
    if profile_snapshot.get("raw_text"):
        return extract_profile_facts(profile_snapshot["raw_text"])["facts"]
    return {}


def _resume_has_experience(profile_snapshot, required_years):
    months = _profile_facts(profile_snapshot).get("total_experience_months")
    if not isinstance(months, int):
        return None
    return months >= required_years * 12


def _certification_met(cert_text, requirement):
    tokens = [token for token in re.findall(r"[a-z0-9]+", requirement.lower())
              if token not in {"certified", "certification"}]
    return bool(tokens) and all(phrase_present(cert_text, token) for token in tokens)


_SUGGESTION_HINTS = {
    "docker": "skills section or project descriptions",
    "kubernetes": "skills section (only if you have exposure)",
    "aws": "skills section or cloud experience subsection",
    "gcp": "skills section or cloud experience subsection",
    "azure": "skills section or cloud experience subsection",
    "terraform": "DevOps/infrastructure skills section",
    "ci/cd": "project descriptions (mention deployment workflows)",
    "kafka": "skills section (only if you have exposure)",
    "redis": "skills section (only if you have exposure)",
    "spark": "skills section (only if you have exposure)",
    "airflow": "skills section (only if you have exposure)",
}


def _active_snapshot():
    try:
        from profile import get_active_profile_snapshot
        return get_active_profile_snapshot()
    except Exception:
        return None


def _as_snapshot(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        extracted = extract_profile_facts(value)
        return {"raw_text": value, "facts": extracted["facts"],
                "readability": extracted["readability"], "status": "review_fixture"}
    return None


def ats_check(resume_profile, jd_text):
    """Compare resume against JD for ATS keyword compatibility.

    Returns dict with: ats_score (int 0-100), found (list), missing (list),
    suggestions (list), truncation_warning (bool).
    """
    snapshot = _as_snapshot(resume_profile)
    facts = _profile_facts(snapshot)
    jd_text = jd_text or ""
    jd_length = len(jd_text.strip())
    truncation_warning = 0 < jd_length < 600

    # Extract tech keywords from JD
    jd_tech_keywords = _extract_tech_keywords(jd_text)

    # Extract non-tech requirements
    experience_reqs = _extract_experience_requirement(jd_text)
    degree_reqs = _extract_degree_requirements(jd_text)
    cert_reqs = _extract_cert_requirements(jd_text)

    profile_skills = {
        (item.get("name") if isinstance(item, dict) else str(item)).casefold()
        for item in facts.get("skills") or []
    }
    raw_resume = (snapshot or {}).get("raw_text") or ""

    # Match tech keywords with boundary-safe synonym expansion.
    tech_found = []
    tech_missing = []
    for kw in jd_tech_keywords:
        synonyms = _expand_synonyms(kw)
        if kw.casefold() in profile_skills or any(phrase_present(raw_resume, syn) for syn in synonyms):
            tech_found.append(kw)
        else:
            tech_missing.append(kw)

    # Match non-tech requirements
    non_tech_found = []
    non_tech_missing = []

    for req in experience_reqs:
        met = _resume_has_experience(snapshot, req["years"])
        if met is True:
            non_tech_found.append(req["value"])
        elif met is False:
            non_tech_missing.append(req["value"])

    for req in degree_reqs:
        levels = {"diploma": 1, "bachelor": 2, "master": 3, "doctorate": 4}
        attained = max((levels.get(item.get("level"), 0)
                        for item in facts.get("education") or []), default=0)
        required = levels.get(req.get("level"), 0)
        if attained and attained >= required:
            non_tech_found.append(req["value"])
        elif attained:
            non_tech_missing.append(req["value"])

    for req in cert_reqs:
        cert_text = " ".join(item.get("name", "") for item in facts.get("certifications") or [])
        if _certification_met(cert_text, req["value"]):
            non_tech_found.append(req["value"])
        elif facts.get("certifications") is not None:
            non_tech_missing.append(req["value"])

    # Calculate score
    total_items = len(jd_tech_keywords) + len(non_tech_found) + len(non_tech_missing)
    found_items = len(tech_found) + len(non_tech_found)
    ats_score = round(found_items / total_items * 100) if total_items > 0 and snapshot else None

    # Generate suggestions
    suggestions = []
    for kw in tech_missing:
        section = _SUGGESTION_HINTS.get(kw.lower(), "your skills section")
        suggestions.append(f"Verify or demonstrate '{kw}' in {section} only if it is true")
    for val in non_tech_missing:
        if "year" in val.lower():
            suggestions.append(
                f"JD requires '{val}' \u2014 verify the reviewed experience dates; "
                f"do not add unsupported duration"
            )
        else:
            suggestions.append(f"JD mentions '{val}' \u2014 verify your resume covers this")

    return {
        "ats_score": ats_score,
        "found": sorted(tech_found + non_tech_found),
        "missing": sorted(tech_missing + non_tech_missing),
        "suggestions": suggestions,
        "experience_reqs": experience_reqs,
        "degree_reqs": degree_reqs,
        "cert_reqs": cert_reqs,
        "truncation_warning": truncation_warning,
        "document_readability": {
            "resume": (snapshot or {}).get("readability", {}).get("status", "unknown"),
            "job_description": "unknown" if jd_length == 0 else "partial" if truncation_warning else "readable",
        },
        "analysis_version": ANALYSIS_VERSION,
    }


def quick_ats(jd_text, profile_snapshot=None):
    """Quick explainable score; None means insufficient JD/profile evidence."""
    return ats_check(profile_snapshot or _active_snapshot(), jd_text)["ats_score"]


# --- Red flags ---
RED_FLAGS = {
    "unpaid": {
        "patterns": ["unpaid", "voluntary", "volunteer", "no stipend", "unpaid internship"],
        "message": "UNPAID — Verify compensation and whether this role meets your goals",
    },
    "overqualified": {
        "patterns": [
            "senior", "lead", "principal", "staff", "5+ years",
            "7+ years", "10+ years", "8+ years", "6+ years",
        ],
        "message": "SENIOR LEVEL — You'll likely be filtered out, apply only if JD duties match",
    },
    "region_locked": {
        "patterns": [
            "us only", "usa only", "eu only", "europe only",
            "us citizen", "clearance required",
            "must be authorized to work in the united states",
        ],
        "message": "REGION LOCKED — Requires specific work authorization you may not have",
    },
    "generic_title": {
        "patterns": [
            "trainee", "management trainee", "graduate trainee",
            "fresher trainee",
        ],
        "message": "GENERIC TITLE — Verify the actual duties and learning value",
    },
    "bond_risk": {
        "patterns": [
            "bond", "service agreement", "minimum commitment",
            "2 year bond", "3 year bond",
        ],
        "message": "BOND — Review the service agreement before accepting",
    },
    "contract_risk": {
        "patterns": [
            "contract", "freelance", "gig", "project-based", "temporary",
        ],
        "message": "CONTRACT/TEMP — Confirm term, benefits, and documentation with the employer",
    },
    "non_english": {
        "patterns": [
            "deutsch", "fran\u00e7ais", "espa\u00f1ola", "wir suchen",
            "aufgaben", "anforderungen", "stellenangebot", "nous recherchons",
            "requisitos", "offre d'emploi",
        ],
        "message": "NON-ENGLISH — Job posting is not in English, likely region-locked",
    },
}


def _extract_tech_keywords(text):
    """Extract canonical technologies with token/phrase boundaries."""
    found = []
    for canonical, aliases in SKILL_ALIASES.items():
        if any(phrase_present(text, alias) for alias in aliases):
            found.append(canonical)
    return sorted(found)


def analyze_noc(title, text):
    """Match a JD against NOC codes. Returns best match with confidence."""
    text_lower = text.lower()
    title_lower = title.lower()
    combined = title_lower + " " + text_lower

    best_code = None
    best_score = 0
    best_matched_duties = []

    for code, info in NOC_CODES.items():
        score = 0
        matched = []

        # Check title keywords
        noc_title_words = info["title"].lower().split()
        title_overlap = sum(1 for w in noc_title_words if w in title_lower)
        if title_overlap >= 2:
            score += 3

        # Check duty phrases
        for duty in info["duties"]:
            if duty in combined:
                score += 1
                matched.append(duty)

        if score > best_score:
            best_score = score
            best_code = code
            best_matched_duties = matched

    if not best_code:
        return {
            "code": None,
            "title": None,
            "confidence": "red",
            "emoji": "\U0001f534",
            "matched_duties": [],
            "message": "No clear NOC match found — generic title with no identifiable skilled duties",
        }

    if best_score >= 5:
        confidence = "green"
        emoji = "\U0001f7e2"
    elif best_score >= 2:
        confidence = "yellow"
        emoji = "\U0001f7e1"
    else:
        confidence = "red"
        emoji = "\U0001f534"

    return {
        "code": best_code,
        "title": NOC_CODES[best_code]["title"],
        "confidence": confidence,
        "emoji": emoji,
        "matched_duties": best_matched_duties,
        "message": f"Best NOC match: **{best_code} — {NOC_CODES[best_code]['title']}** {emoji}",
    }


def analyze_skills(text, profile_snapshot=None):
    """Explain JD skill evidence against the reviewed active PDF profile."""
    jd_keywords = _extract_tech_keywords(text)
    facts = _profile_facts(_as_snapshot(profile_snapshot))
    profile_skills = {
        (item.get("name") if isinstance(item, dict) else str(item)).casefold()
        for item in facts.get("skills") or []
    }
    matched = [keyword for keyword in jd_keywords if keyword.casefold() in profile_skills]
    gaps = [keyword for keyword in jd_keywords if keyword.casefold() not in profile_skills]

    total = len(jd_keywords)
    match_pct = round(len(matched) / total * 100) if total > 0 and facts else None

    return {
        "matched": sorted(matched),
        "gaps": sorted(gaps),
        "total_required": total,
        "match_percentage": match_pct,
        "status": "unknown" if match_pct is None else "measured",
    }


def detect_red_flags(title, text):
    """Scan for red flag patterns in the JD."""
    combined = (title + " " + text).lower()
    flags = []

    for flag_type, info in RED_FLAGS.items():
        for pattern in info["patterns"]:
            if pattern in combined:
                flags.append({
                    "type": flag_type,
                    "trigger": pattern,
                    "message": info["message"],
                })
                break  # one flag per category

    return flags


def get_verdict(eligibility, skill_result, flags):
    """Generate final verdict based on all analyses."""
    critical_flags = {"unpaid", "region_locked", "non_english"}
    has_critical = any(f["type"] in critical_flags for f in flags)

    eligibility_failed = eligibility.get("status") == "not_met"
    match = skill_result.get("match_percentage")

    if has_critical or eligibility_failed:
        return "skip", "\u274c SKIP", "Critical red flags detected"
    elif match is None:
        return "unknown", "❔ REVIEW", "Insufficient job-description or active-profile evidence"
    elif match >= 60 and len(flags) == 0:
        return "apply", "\u2705 APPLY", "Strong evidence-backed match with no mandatory mismatch"
    elif match >= 60:
        return "caution", "\u26a0\ufe0f APPLY WITH CAUTION", "Good match but some flags to watch"
    else:
        return "caution", "\u26a0\ufe0f REVIEW", f"Only {match}% of explicit skill requirements matched"


def _mandatory_eligibility(profile_snapshot, description):
    facts = _profile_facts(_as_snapshot(profile_snapshot))
    criteria = []
    for req in _extract_experience_requirement(description):
        met = _resume_has_experience(_as_snapshot(profile_snapshot), req["years"])
        status = "met" if met is True else "not_met" if met is False else "unknown"
        criteria.append({**req, "status": status})

    levels = {"diploma": 1, "bachelor": 2, "master": 3, "doctorate": 4}
    attained = max((levels.get(item.get("level"), 0)
                    for item in facts.get("education") or []), default=0)
    for req in _extract_degree_requirements(description):
        required = levels.get(req["level"], 0)
        status = ("unknown" if not attained else "met" if attained >= required else "not_met")
        criteria.append({**req, "status": status})

    certs = " ".join(item.get("name", "") for item in facts.get("certifications") or [])
    for req in _extract_cert_requirements(description):
        if not facts:
            status = "unknown"
        else:
            status = "met" if _certification_met(certs, req["value"]) else "not_met"
        criteria.append({**req, "status": status})

    mandatory = [criterion for criterion in criteria if criterion.get("required")]
    status = ("not_met" if any(c["status"] == "not_met" for c in mandatory) else
              "unknown" if any(c["status"] == "unknown" for c in mandatory) else "met")
    overall = {"met": "passed", "not_met": "failed", "unknown": "review"}[status]
    return {"status": status, "overall": overall, "criteria": criteria,
            "note": "Unknown evidence is not treated as a failure."}


def full_analyze(title, description, profile_snapshot=None, location=""):
    """Return separate readability, eligibility, match, and regional lanes."""
    profile_snapshot = _as_snapshot(profile_snapshot) or _active_snapshot()
    ats = ats_check(profile_snapshot, description)
    skills = analyze_skills(description, profile_snapshot)
    eligibility = _mandatory_eligibility(profile_snapshot, description)
    flags = detect_red_flags(title, description)
    verdict_key, verdict_label, verdict_reason = get_verdict(eligibility, skills, flags)

    # Canada NOC is a separate regional lane and never affects India fit.
    location_lower = (location or "").lower()
    noc = analyze_noc(title, description) if re.search(r"\bcanada\b|\bcanadian\b", location_lower) else None

    return {
        "analysis_version": ANALYSIS_VERSION,
        "document_readability": ats["document_readability"],
        "mandatory_eligibility": eligibility,
        "resume_jd_match": {
            "score": ats["ats_score"], "matched": ats["found"],
            "missing": ats["missing"], "suggestions": ats["suggestions"],
        },
        "noc": noc,
        "skills": skills,
        "red_flags": flags,
        "verdict": verdict_key,
        "verdict_label": verdict_label,
        "verdict_reason": verdict_reason,
    }
