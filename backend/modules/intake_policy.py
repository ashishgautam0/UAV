"""User's intake preferences, independent of resume-match scoring.

Company exclusions are an explicit, maintained list, not a claim that every
international startup is a large MNC. Unknown employers remain eligible.
"""
import html
import re
import unicodedata

# Match employer names only, never technologies or clients mentioned in a JD.
LARGE_MNC_ALIASES = (
    "Accenture", "TCS", "Tata Consultancy Services", "Infosys", "Wipro",
    "HCL", "HCLTech", "HCL Technologies", "Tech Mahindra", "Cognizant",
    "Capgemini", "IBM", "International Business Machines", "DXC Technology",
    "LTIMindtree", "LTI Mindtree", "Larsen & Toubro Infotech", "Mindtree",
    "Mphasis", "NTT", "NTT Data", "NTT Data Services", "NTT Data Information Processing",
    "Deloitte", "Deloitte USI", "EY", "Ernst & Young", "KPMG", "PwC",
    "PricewaterhouseCoopers", "Amazon", "Amazon Web Services", "AWS",
    "Amazon Development Centre", "Amazon Development Center",
    "Amazon Development Centre India", "Amazon Development Center India",
    "Google", "Google India", "Microsoft", "Microsoft India", "Meta",
    "Meta Platforms", "Apple", "Oracle", "SAP", "Salesforce", "Adobe",
    "Cisco", "Intel", "Nvidia", "Qualcomm", "Samsung", "Samsung Electronics",
    "Dell", "Dell Technologies", "HP", "Hewlett Packard", "Hewlett Packard Enterprise",
    "HPE", "ServiceNow", "VMware", "Broadcom", "Siemens", "Bosch",
    "Robert Bosch", "Robert Bosch Engineering and Business Solutions",
    "Philips", "Roche", "Novartis", "Pfizer", "AstraZeneca",
    "Barclays", "HSBC", "Standard Chartered", "JPMorgan Chase",
    "JP Morgan", "J P Morgan", "J P Morgan Chase", "JPMorgan Chase & Co",
    "Goldman Sachs", "Morgan Stanley", "Citi", "Citibank", "Deutsche Bank",
    "UBS", "BNP Paribas", "Wells Fargo", "Bank of America",
    "American Express", "Mastercard", "Visa", "PayPal", "Genpact",
    "HTC Global Services", "UST", "UST Global", "Persistent Systems",
    "Virtusa", "EPAM", "EPAM Systems", "Publicis Sapient",
)
_SUFFIX = re.compile(
    r"\s+(?:private limited|pvt ltd|pvt limited|private ltd|limited|ltd|incorporated|inc|"
    r"corporation|corp|llc|llp|plc|gmbh|india)$"
)

def normalize_employer(value):
    value = unicodedata.normalize("NFKC", html.unescape(value or "")).casefold()
    value = re.sub(r"[^\w]+", " ", value).strip()
    while True:
        trimmed = _SUFFIX.sub("", value).strip()
        if trimmed == value:
            return value
        value = trimmed

_EXCLUDED = {normalize_employer(name) for name in LARGE_MNC_ALIASES}

def excluded_employer(company, company_exclusions=()):
    normalized = normalize_employer(company)
    return normalized in _EXCLUDED or bool(normalized and normalized in {
        normalize_employer(name) for name in company_exclusions
    })

_NUMBER = r"\d+(?:\.\d+)?"
_DURATION = (
    rf"(?P<strict>more than|over|greater than|>)?\s*"
    rf"(?P<low>{_NUMBER})\s*(?:\+|(?:-|–|—|to)\s*(?P<high>{_NUMBER}))?\s*"
    r"(?P<unit>years?|yrs?|months?|mos?)"
)
# Work/technical modifiers allowed, but do not span another sentence or number.
_AFTER = re.compile(
    _DURATION + r"\s*(?:of\s+)?(?:[a-z]+[\s/-]+){0,5}(?:experience|exp\b)", re.I
)
_BEFORE = re.compile(
    r"\b(?:experience|exp)\s*(?:required|requirement|minimum)?\s*[:=-]\s*" + _DURATION,
    re.I,
)
_OPTIONAL = re.compile(r"\b(?:preferred|preferably|desirable|nice to have|optional|a plus)\b", re.I)
_REQUIRED = re.compile(r"\b(?:must|required|mandatory|minimum|at least|essential)\b", re.I)
_UPPER = re.compile(r"(?:up to|at most|maximum|less than|under|no more than)\s*$", re.I)
_WORD_NUMBERS = {"one": "1", "two": "2", "three": "3", "four": "4",
                 "five": "5", "six": "6", "seven": "7", "eight": "8",
                 "nine": "9", "ten": "10"}

def experience_exclusion(description):
    """Return evidence for a required experience band above 24 months, otherwise None.

    Unknown experience is retained. Preferred sections are optional unless an
    individual clause explicitly says required. Upper bounds do not exclude.
    """
    text = html.unescape(description or "")
    text = re.sub(r"<[^>]+>", "\n", text)
    text = re.sub(r"\b(" + "|".join(_WORD_NUMBERS) + r")\b",
                  lambda m: _WORD_NUMBERS[m.group().lower()], text, flags=re.I)
    section_optional = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) < 85 and re.fullmatch(
            r"(?:preferred|desired|desirable|nice.to.have|optional)(?:\s+\w+){0,4}\s*:?", line, re.I
        ):
            section_optional = True
            continue
        if len(line) < 85 and re.fullmatch(
            r"(?:required|minimum|basic|essential|mandatory)(?:\s+\w+){0,4}\s*:?", line, re.I
        ):
            section_optional = False
            continue
        for clause in re.split(r";|(?<!\d)\.(?!\d)|\bbut\b", line):
            for pattern in (_AFTER, _BEFORE):
                for match in pattern.finditer(clause):
                    # Local qualification only: a later 'Python preferred' must
                    # not erase a preceding '2 years required'.
                    tail = clause[match.end():]
                    local = clause[max(0, match.start()-35):match.end()]
                    local += re.split(r",|\band\b", tail, maxsplit=1)[0]
                    if _UPPER.search(clause[:match.start()]) or re.search(r"\bno\s*$", clause[:match.start()], re.I):
                        continue
                    if (_OPTIONAL.search(local) or section_optional) and not _REQUIRED.search(local):
                        continue
                    months = float(match["high"] or match["low"]) * (12 if match["unit"].lower().startswith(("year", "yr")) else 1)
                    if months > 24 or (months == 24 and match["strict"]):
                        return match.group().strip()
    return None

def exclusion_reason(job, company_exclusions=()):
    if excluded_employer(job.get("company"), company_exclusions):
        if normalize_employer(job.get("company")) in _EXCLUDED:
            return "excluded large multinational employer"
        return "excluded by Settings company list"
    evidence = experience_exclusion(job.get("description"))
    if evidence:
        return "experience requirement above two years: " + evidence
    return None

def filter_jobs(jobs, company_exclusions=()):
    kept, excluded = [], []
    for job in jobs:
        reason = exclusion_reason(job, company_exclusions)
        if reason:
            excluded.append((job, reason))
        else:
            kept.append(job)
    return kept, excluded
