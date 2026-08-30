from fastapi import APIRouter, Query

from ..models.schemas import CompanyResearchRequest
from company_research import research_company
from email_finder import find_emails
from tracker import get_cached_research, save_research_cache

router = APIRouter()


@router.get("/cached")
def cached_intel(name: str = Query(...)):
    """Company intel from the cache only (written by the hourly routine).

    Returns {"found": false} instead of 404 when nothing fresh is cached —
    the job page treats that as "not researched yet".
    """
    row = get_cached_research(name)
    if not row:
        return {"found": False}
    return {"found": True, **row}


@router.get("/recruiter-emails")
def recruiter_emails(
    company: str = Query(...),
    names: str = Query("", description="extra recruiter names, ';'-separated"),
    domain: str = Query("", description="override the company email domain"),
):
    """Guess + (where port 25 is open) verify recruiter email addresses.

    Domain and a default recruiter name are taken from cached company intel;
    the caller may add more names or override the domain. Computed live —
    nothing is stored, so results never go stale.
    """
    intel = get_cached_research(company) or {}
    dom = (domain or intel.get("product_url") or "").strip()
    if not dom:
        return {"ok": False, "reason": "no_domain",
                "message": "No company website/domain known yet."}

    name_list = [n.strip() for n in names.split(";") if n.strip()]
    stored = (intel.get("hiring_contact_name") or "").strip()
    if stored and stored not in name_list:
        name_list.insert(0, stored)
    if not name_list:
        return {"ok": False, "reason": "no_names",
                "message": "No recruiter name known yet — add one to search."}

    report = find_emails(dom, name_list)
    report["ok"] = True
    return report


@router.post("")
def research(
    body: CompanyResearchRequest,
):
    cached = get_cached_research(body.company_name)
    if cached:
        return cached

    result = research_company(body.company_name)
    if result.get("description"):
        save_research_cache(body.company_name, result)

    return result
