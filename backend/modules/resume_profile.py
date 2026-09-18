"""PDF-derived, reviewable resume profiles and evidence-preserving facts.

This module is intentionally deterministic.  It does not call an LLM or OCR:
the uploaded PDF remains the only resume source, extracted text is immutable,
and user corrections are stored separately from the extracted facts.
"""

from __future__ import annotations

import re
from calendar import month_abbr
from datetime import date


PROFILE_SCHEMA_VERSION = 1
PARSER_VERSION = "pdf-profile-v1"

_MONTHS = {name.lower(): index for index, name in enumerate(month_abbr) if name}
_MONTHS.update({
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12, "sept": 9,
})
_MONTH_TOKEN = "(?:" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + ")"
_DATE_RANGE_RE = re.compile(
    rf"(?:(?P<sm>{_MONTH_TOKEN})\s+)?(?P<sy>(?:19|20)\d{{2}})\s*"
    rf"[-–—]\s*(?:(?:(?P<em>{_MONTH_TOKEN})\s+)?(?P<ey>(?:19|20)\d{{2}})|"
    rf"(?P<present>present|current|now))",
    re.IGNORECASE,
)
_EXPERIENCE_CLAIM_RE = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s*\+?\s*years?\s+(?:of\s+)?(?:professional\s+)?experience(?!\w)",
    re.IGNORECASE,
)

_SECTION_NAMES = {
    "experience": {"experience", "work experience", "professional experience", "employment"},
    "education": {"education", "academic background", "academics"},
    "skills": {"skills", "technical skills", "core skills", "technologies"},
    "certifications": {"certifications", "certificates", "licenses & certifications"},
    "projects": {"projects", "selected projects", "personal projects"},
}
_ALL_HEADINGS = {heading for values in _SECTION_NAMES.values() for heading in values}

# Vocabulary is used only to extract evidence from the uploaded PDF.  It is
# never treated as a default candidate skill list.
SKILL_ALIASES = {
    "python": ("python",), "java": ("java",), "javascript": ("javascript", "js"),
    "typescript": ("typescript", "ts"), "go": ("golang", "go"),
    "c++": ("c++", "cpp"), "c#": ("c#", "csharp"),
    "react": ("react", "react.js", "reactjs"),
    "next.js": ("next.js", "nextjs"), "node.js": ("node.js", "nodejs"),
    "fastapi": ("fastapi", "fast api"), "django": ("django",), "flask": ("flask",),
    "sql": ("sql", "structured query language"), "postgresql": ("postgresql", "postgres"),
    "mongodb": ("mongodb", "mongo db"), "redis": ("redis",),
    "docker": ("docker", "containerization"), "kubernetes": ("kubernetes", "k8s"),
    "aws": ("aws", "amazon web services"), "azure": ("microsoft azure", "azure"),
    "gcp": ("google cloud platform", "google cloud", "gcp"),
    "terraform": ("terraform",), "git": ("git", "version control"),
    "machine learning": ("machine learning", "ml"),
    "deep learning": ("deep learning", "dl"),
    "natural language processing": ("natural language processing", "nlp"),
    "computer vision": ("computer vision",),
    "pytorch": ("pytorch",), "tensorflow": ("tensorflow",),
    "scikit-learn": ("scikit-learn", "scikit learn", "sklearn"),
    "pandas": ("pandas",), "numpy": ("numpy",),
    "langchain": ("langchain", "lang chain"), "langgraph": ("langgraph", "lang graph"),
    "rag": ("retrieval-augmented generation", "retrieval augmented generation", "rag"),
    "llm": ("large language models", "large language model", "llm"),
    "generative ai": ("generative ai", "genai", "gen ai"),
    "rest api": ("restful api", "rest api"), "graphql": ("graphql", "graph ql"),
    "kafka": ("apache kafka", "kafka"), "spark": ("apache spark", "pyspark", "spark"),
    "airflow": ("apache airflow", "airflow"), "etl": ("extract transform load", "etl"),
    "web scraping": ("web scraping",), "automation": ("automation",),
}


def phrase_pattern(phrase: str) -> re.Pattern:
    """Boundary-safe matcher; avoids go→MongoDB, rag→storage, sql→NoSQL."""
    escaped = re.escape(phrase.strip()).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)


def phrase_present(text: str, phrase: str) -> bool:
    return bool(phrase_pattern(phrase).search(text or ""))


def _clean_lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip(" •\t") for line in (text or "").splitlines()
            if re.sub(r"\s+", " ", line).strip(" •\t")]


def _section(lines: list[str], section: str) -> list[tuple[int, str]]:
    wanted = _SECTION_NAMES[section]
    start = None
    out = []
    for index, line in enumerate(lines):
        normalized = line.lower().rstrip(":")
        if normalized in wanted:
            start = index + 1
            continue
        if start is not None and normalized in _ALL_HEADINGS:
            break
        if start is not None:
            out.append((index, line))
    return out


def _evidence(excerpt: str, line: int, source: str = "pdf_text") -> list[dict]:
    return [{"source": source, "line": line + 1, "excerpt": excerpt[:500]}]


def _month_index(year: int, month: int) -> int:
    return year * 12 + month - 1


def _months_between(start: int, end: int) -> int:
    return max(end - start + 1, 0)


def _union_months(intervals: list[tuple[int, int]]) -> int | None:
    if not intervals:
        return None
    merged = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(_months_between(start, end) for start, end in merged)


def _date_value(match: re.Match, prefix: str, today: date) -> tuple[str, int]:
    if prefix == "end" and match.group("present"):
        return "present", _month_index(today.year, today.month)
    year = int(match.group("sy" if prefix == "start" else "ey"))
    month_token = match.group("sm" if prefix == "start" else "em")
    if not month_token:
        return str(year), _month_index(year, 1 if prefix == "start" else 12)
    month = _MONTHS.get((month_token or "").lower(), 1 if prefix == "start" else 12)
    return f"{year:04d}-{month:02d}", _month_index(year, month)


def _extract_experience(lines: list[str], today: date) -> tuple[list[dict], int | None, list[dict]]:
    rows = _section(lines, "experience")
    facts = []
    intervals = []
    for row_index, (line_index, line) in enumerate(rows):
        match = _DATE_RANGE_RE.search(line)
        if not match:
            continue
        start_label, start_value = _date_value(match, "start", today)
        end_label, end_value = _date_value(match, "end", today)
        if end_value < start_value:
            continue
        exact_dates = bool(match.group("sm")) and (bool(match.group("em")) or bool(match.group("present")))
        prior = rows[row_index - 1][1] if row_index else ""
        label = prior if prior and not _DATE_RANGE_RE.search(prior) else line[:match.start()].strip(" ,-–—")
        excerpt = " | ".join(part for part in (prior, line) if part)
        fact = {
            "id": f"experience-{line_index + 1}", "label": label or "Experience entry",
            "company": "", "role": "", "start": start_label, "end": end_label,
            "months": _months_between(start_value, end_value) if exact_dates else None,
            "date_precision": "month" if exact_dates else "year_only_requires_review",
            "evidence": _evidence(excerpt, line_index),
        }
        facts.append(fact)
        if exact_dates:
            intervals.append((start_value, end_value))

    claimed = []
    for line_index, line in enumerate(lines):
        for match in _EXPERIENCE_CLAIM_RE.finditer(line):
            claimed.append((round(float(match.group(1)) * 12), line_index, line))
    total = _union_months(intervals)
    if claimed:
        claimed_months, line_index, line = max(claimed)
        total = max(total or 0, claimed_months)
    claims = [{"months": months, "evidence": _evidence(line, line_index)}
              for months, line_index, line in claimed]
    return facts, total, claims


def _degree_level(line: str) -> str | None:
    if re.search(r"(?<!\w)(ph\.?d\.?|doctorate|doctoral)(?!\w)", line, re.I):
        return "doctorate"
    if re.search(r"(?<!\w)(m\.?tech|m\.?s\.?|m\.?sc|master'?s?)(?!\w)", line, re.I):
        return "master"
    if re.search(r"(?<!\w)(b\.?tech|b\.?e\.?|b\.?s\.?|bachelor'?s?)(?!\w)", line, re.I):
        return "bachelor"
    if re.search(r"(?<!\w)(diploma|associate)(?!\w)", line, re.I):
        return "diploma"
    return None


def _extract_education(lines: list[str]) -> list[dict]:
    rows = _section(lines, "education") or list(enumerate(lines))
    facts = []
    for line_index, line in rows:
        level = _degree_level(line)
        if level:
            facts.append({
                "id": f"education-{line_index + 1}", "level": level,
                "credential": line, "field": "", "institution": "",
                "evidence": _evidence(line, line_index),
            })
    return facts


def _extract_skills(lines: list[str]) -> list[dict]:
    text = "\n".join(lines)
    facts = []
    for canonical, aliases in SKILL_ALIASES.items():
        match = None
        for alias in aliases:
            match = phrase_pattern(alias).search(text)
            if match:
                break
        if match:
            line_index = text[:match.start()].count("\n")
            facts.append({
                "name": canonical,
                "evidence": _evidence(lines[min(line_index, len(lines) - 1)], line_index),
            })
    return sorted(facts, key=lambda row: row["name"])


def _extract_certifications(lines: list[str]) -> list[dict]:
    rows = _section(lines, "certifications")
    if not rows:
        rows = [(index, line) for index, line in enumerate(lines)
                if re.search(r"\b(certif(?:ied|ication)|credential)\b", line, re.I)]
    return [{"name": line, "evidence": _evidence(line, index)} for index, line in rows]


def extract_profile_facts(text: str, *, page_count: int = 1,
                          pages_with_text: int | None = None,
                          today: date | None = None) -> dict:
    """Extract reviewable facts while retaining an evidence excerpt per fact."""
    today = today or date.today()
    lines = _clean_lines(text)
    experience, total_months, experience_claims = _extract_experience(lines, today)
    pages_with_text = pages_with_text if pages_with_text is not None else (1 if text.strip() else 0)
    replacement_ratio = (text.count("�") / max(len(text), 1))
    readability_status = "readable"
    warnings = []
    if len(text.strip()) < 100 or pages_with_text == 0:
        readability_status = "unreadable"
        warnings.append("PDF has insufficient selectable text; OCR is not available.")
    elif pages_with_text < page_count or replacement_ratio > 0.01:
        readability_status = "review"
        warnings.append("Some pages or characters may not have extracted cleanly.")

    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "parser_version": PARSER_VERSION,
        "facts": {
            "skills": _extract_skills(lines),
            "experience": experience,
            "total_experience_months": total_months,
            "experience_claims": experience_claims,
            "education": _extract_education(lines),
            "certifications": _extract_certifications(lines),
        },
        "readability": {
            "status": readability_status, "characters": len(text),
            "pages": page_count, "pages_with_text": pages_with_text,
            "replacement_character_ratio": round(replacement_ratio, 5),
            "warnings": warnings,
        },
    }


def merge_reviewed_facts(extracted: dict, corrections: dict | None) -> dict:
    """Overlay structured corrections without modifying extracted evidence."""
    base = dict((extracted or {}).get("facts") or {})
    corrections = corrections or {}
    for field in ("skills", "experience", "education", "certifications"):
        if field in corrections:
            base[field] = corrections[field]
    if "total_experience_months" in corrections:
        value = corrections["total_experience_months"]
        base["total_experience_months"] = value if isinstance(value, int) and value >= 0 else None
    return base


def reviewed_experience_months(entries: list[dict], today: date | None = None) -> int | None:
    """Calculate non-overlapping months from reviewed YYYY-MM dates."""
    today = today or date.today()
    intervals = []
    for entry in entries or []:
        start = str(entry.get("start") or "")
        end = str(entry.get("end") or "")
        if not re.fullmatch(r"(?:19|20)\d{2}-(?:0[1-9]|1[0-2])", start):
            continue
        if end == "present":
            end = f"{today.year:04d}-{today.month:02d}"
        if not re.fullmatch(r"(?:19|20)\d{2}-(?:0[1-9]|1[0-2])", end):
            continue
        sy, sm = map(int, start.split("-"))
        ey, em = map(int, end.split("-"))
        left, right = _month_index(sy, sm), _month_index(ey, em)
        if right >= left:
            intervals.append((left, right))
    return _union_months(intervals) if intervals else None


def profile_text(snapshot: dict | None) -> str:
    """Render one reviewed snapshot plus immutable PDF evidence, with no fallback."""
    if not snapshot:
        return ""
    facts = snapshot.get("facts") or {}
    lines = [f"ACTIVE REVIEWED PDF PROFILE VERSION: {snapshot.get('version', 'unknown')}"]
    skills = [item.get("name", "") for item in facts.get("skills") or [] if item.get("name")]
    if skills:
        lines.append("Verified skills: " + ", ".join(skills))
    for item in facts.get("experience") or []:
        label = item.get("label") or " ".join(part for part in (item.get("role"), item.get("company")) if part)
        lines.append(f"Verified experience: {label} [{item.get('start', '')} to {item.get('end', '')}]")
    months = facts.get("total_experience_months")
    if isinstance(months, int):
        lines.append(f"Verified non-overlapping experience duration: {months} months")
    for item in facts.get("education") or []:
        label = " — ".join(part for part in (item.get("credential"), item.get("field"), item.get("institution")) if part)
        lines.append(f"Verified education ({item.get('level', 'unknown')}): {label}")
    for item in facts.get("certifications") or []:
        if item.get("name"):
            lines.append("Verified certification: " + item["name"])
    raw = (snapshot.get("raw_text") or "").strip()
    if raw:
        lines.extend(("SOURCE PDF TEXT (supporting evidence; do not embellish):", raw))
    return "\n".join(lines) if raw or len(lines) > 1 else ""
