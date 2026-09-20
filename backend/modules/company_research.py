"""Find a company's official website and a real hiring contact."""

try:
    from googlesearch import search as gsearch
except ImportError:
    gsearch = None

def research_company(company_name, company_domain=None):
    """Return only a website URL and hiring-contact fields."""
    if company_domain:
        website = str(company_domain).strip()
        if not website.startswith(("https://", "http://")):
            website = f"https://{website}"
        return {
            "company_name": company_name,
            "product_url": website,
            "hiring_contact": {"name": "", "title": "", "linkedin_url": ""},
        }
    if gsearch is None:
        return _empty_result(company_name)

    result = _empty_result(company_name)

    try:
        websites = list(gsearch(
            f'"{company_name}" official website',
            num_results=3, lang="en"
        ))
        if websites:
            result["product_url"] = websites[0]

        contacts = list(gsearch(
            f'"{company_name}" recruiter OR "hiring manager" site:linkedin.com/in',
            num_results=3, lang="en"
        ))
        for url in contacts:
            if "linkedin.com/in/" not in url:
                continue
            slug = url.split("linkedin.com/in/", 1)[1].split("?", 1)[0].strip("/")
            result["hiring_contact"] = {
                "name": slug.replace("-", " ").title(),
                "title": "",
                "linkedin_url": url,
            }
            break

    except Exception as e:
        print(f"Company website lookup failed for {company_name}: {e}")

    return result


def _empty_result(company_name):
    return {
        "company_name": company_name,
        "product_url": "",
        "hiring_contact": {"name": "", "title": "", "linkedin_url": ""},
    }