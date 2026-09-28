"""Recruiter email finder.

Given a company domain and recruiter names, generate the common corporate
address patterns, check the domain actually receives mail (MX via
DNS-over-HTTPS, so it works behind egress proxies), and — where outbound
port 25 is open — verify candidates against the MX with RCPT TO, including
catch-all detection. Verification never sends an email.

Statuses per candidate:
  valid      SMTP accepted exactly this mailbox (and the domain is not catch-all)
  catch_all  the server accepts every address, so acceptance proves nothing
  invalid    SMTP rejected the mailbox
  pattern    could not SMTP-verify (port blocked / greylisted); MX exists,
             so this is an educated pattern guess and NOT evidence. Outbound
             port 25 is blocked on both Vercel and the routine container, so
             in this deployment every candidate comes back as "pattern" —
             treat the whole report as a lead to check by hand, never as a
             verified recipient. `extract_published_emails` is the evidence
             path; this is not.
  no_mx      the domain has no mail setup at all

CLI:
  python email_finder.py verify --domain acme.com --names "Priya Sharma;Rahul K"
prints a JSON report on stdout.
"""

import argparse
import json
import random
import re
import smtplib
import socket
import string
import sys
import unicodedata

# `requests` is imported inside mx_lookup, not here: extract_published_emails
# needs only `re`, and the dependency-light CI lanes that exercise it install
# no third-party packages.

DOH_ENDPOINTS = [
    "https://dns.google/resolve",
    "https://cloudflare-dns.com/dns-query",
]

# Ordered by how common each pattern is in the wild.
PATTERNS = [
    "{first}.{last}",
    "{first}",
    "{first}{last}",
    "{f}{last}",
    "{first}_{last}",
    "{first}.{l}",
    "{last}.{first}",
]

HELO_DOMAIN = "uav-6qe7.vercel.app"
SMTP_TIMEOUT = 8


# Addresses an employer published in its own job description are the only
# recipient evidence that costs nothing to obtain: the employer wrote them on
# the posting itself. These are harvested, never constructed.
_EMAIL_IN_TEXT = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
)
# Mailboxes that appear in postings but are not a hiring contact.
_NON_HIRING_LOCALS = frozenset({
    "noreply", "no-reply", "donotreply", "do-not-reply", "support", "help",
    "helpdesk", "info", "sales", "billing", "invoice", "accounts", "legal",
    "privacy", "security", "abuse", "webmaster", "postmaster", "marketing",
    "newsletter", "subscribe", "unsubscribe", "feedback",
})
# Job boards and mail providers — an address here is not the employer's.
_NON_EMPLOYER_DOMAINS = frozenset({
    "gmail.com", "yahoo.com", "yahoo.co.in", "hotmail.com", "outlook.com",
    "live.com", "rediffmail.com", "protonmail.com", "icloud.com",
    "naukri.com", "indeed.com", "linkedin.com", "shine.com", "glassdoor.com",
    "monster.com", "instahyre.com", "cutshort.io", "wellfound.com",
    "apna.co", "unstop.com", "example.com",
})


def extract_published_emails(text):
    """Employer addresses the job description itself publishes, in order.

    Drops duplicates, obvious non-hiring mailboxes (noreply@, support@) and
    free-mail or job-board domains, which belong to the board or an individual
    rather than the hiring employer. Returns [] when the posting has none —
    this harvests what is written, it never guesses a pattern.
    """
    seen, out = set(), []
    for raw in _EMAIL_IN_TEXT.findall(str(text or "")):
        email = raw.strip(".,;:()<>[]'\"").lower()
        if email in seen:
            continue
        seen.add(email)
        local, _, domain = email.partition("@")
        if local in _NON_HIRING_LOCALS or domain in _NON_EMPLOYER_DOMAINS:
            continue
        out.append(email)
    return out


def _ascii(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def normalize_name(name):
    """'Priya  Sharma-Rao' -> ('priya', 'sharmarao'); single names get last=''. """
    clean = re.sub(r"[^a-z ]", "", _ascii(name).lower().replace("-", ""))
    parts = [p for p in clean.split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


def candidates_for(name, domain):
    first, last = normalize_name(name)
    if not first:
        return []
    out = []
    for pat in PATTERNS:
        if not last and ("{last}" in pat or "{l}" in pat):
            continue
        local = pat.format(first=first, last=last, f=first[:1], l=last[:1])
        email = f"{local}@{domain}"
        if email not in out:
            out.append(email)
    return out


def mx_lookup(domain, timeout=6):
    """MX hosts sorted by priority, via DNS-over-HTTPS (proxy-friendly)."""
    import requests

    for endpoint in DOH_ENDPOINTS:
        try:
            resp = requests.get(
                endpoint,
                params={"name": domain, "type": "MX"},
                headers={"accept": "application/dns-json"},
                timeout=timeout,
            )
            answers = resp.json().get("Answer") or []
        except Exception:
            continue
        hosts = []
        for a in answers:
            if a.get("type") != 15:
                continue
            bits = (a.get("data") or "").split()
            if len(bits) == 2:
                try:
                    hosts.append((int(bits[0]), bits[1].rstrip(".")))
                except ValueError:
                    pass
        if hosts:
            return [h for _, h in sorted(hosts)]
        if answers is not None:
            return []  # authoritative empty answer
    return None  # every resolver failed — unknown


class _SmtpSession:
    """One connection to an MX, reused for every RCPT probe."""

    def __init__(self, mx_host):
        self.smtp = smtplib.SMTP(timeout=SMTP_TIMEOUT)
        self.smtp.connect(mx_host, 25)
        self.smtp.ehlo(HELO_DOMAIN)
        # Null reverse-path: standard for verification, sends nothing and
        # exposes no real address.
        code, _ = self.smtp.mail("<>")
        if code >= 400:
            self.smtp.mail(f"<verify@{HELO_DOMAIN}>")

    def rcpt(self, email):
        code, _ = self.smtp.rcpt(f"<{email}>")
        if code in (250, 251):
            return "valid"
        if code in (550, 551, 553):
            return "invalid"
        return "unknown"

    def close(self):
        try:
            self.smtp.quit()
        except Exception:
            pass


def _random_local():
    return "zz" + "".join(random.choices(string.ascii_lowercase + string.digits, k=14))


def find_emails(domain, names):
    """Full report dict for a domain + list of recruiter names."""
    domain = domain.strip().lower().lstrip("@")
    domain = re.sub(r"^https?://", "", domain).split("/")[0]
    domain = domain.removeprefix("www.")

    mx_hosts = mx_lookup(domain)
    report = {
        "domain": domain,
        "mx_ok": bool(mx_hosts),
        "mx_hosts": mx_hosts or [],
        "smtp_checked": False,
        "catch_all": None,
        "email_pattern": None,
        "contacts": [],
    }

    session = None
    if mx_hosts:
        for host in mx_hosts[:2]:
            try:
                session = _SmtpSession(host)
                report["smtp_checked"] = True
                break
            except (OSError, smtplib.SMTPException, socket.timeout):
                session = None

    if session:
        try:
            report["catch_all"] = session.rcpt(f"{_random_local()}@{domain}") == "valid"
        except Exception:
            session.close()
            session = None
            report["smtp_checked"] = False

    fallback = "pattern" if mx_hosts else ("no_mx" if mx_hosts == [] else "pattern")

    for name in names:
        cands = candidates_for(name, domain)
        entry = {"name": name.strip(), "candidates": []}
        for email in cands:
            status = fallback
            if session:
                try:
                    status = session.rcpt(email)
                except Exception:
                    session.close()
                    session = None
                    status = fallback
                if status == "valid" and report["catch_all"]:
                    status = "catch_all"
            entry["candidates"].append({"email": email, "status": status})
        # Put confirmed-valid candidates first, keep pattern order otherwise.
        entry["candidates"].sort(key=lambda c: 0 if c["status"] == "valid" else 1)
        report["contacts"].append(entry)

    if session:
        session.close()

    # If any mailbox verified, record which pattern it matched so the same
    # pattern can be applied to other people at this company.
    for entry in report["contacts"]:
        for cand in entry["candidates"]:
            if cand["status"] != "valid":
                continue
            first, last = normalize_name(entry["name"])
            local = cand["email"].split("@")[0]
            for pat in PATTERNS:
                built = pat.format(first=first, last=last or "", f=first[:1],
                                   l=(last or " ")[:1])
                if built == local:
                    report["email_pattern"] = pat
                    break
            if report["email_pattern"]:
                break
        if report["email_pattern"]:
            break

    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_v = sub.add_parser("verify", help="pattern-guess + verify recruiter emails")
    p_v.add_argument("--domain", required=True, help="company domain, e.g. acme.com")
    p_v.add_argument("--names", required=True,
                     help="semicolon-separated full names, e.g. 'A B;C D'")
    args = parser.parse_args()

    names = [n for n in (s.strip() for s in args.names.split(";")) if n]
    if not names:
        print("No names given.", file=sys.stderr)
        return 1
    report = find_emails(args.domain, names)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
