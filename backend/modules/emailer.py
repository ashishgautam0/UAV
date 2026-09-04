"""Email delivery for the hourly run summary.

Sends the same summary the routine pushes in-app/to the phone to an email inbox
as well. Two backends, chosen by which credential is set; if neither is set the
function no-ops (like the VAPID push), so runs never break:

  1. Resend  — set RESEND_API_KEY. HTTPS to api.resend.com, so it works through
     the routine's outbound proxy even when SMTP ports are blocked. This is the
     recommended path. The sender is NOTIFY_EMAIL_FROM (default the shared
     Resend sandbox sender, which can deliver to your own address for testing).
  2. Gmail SMTP — set SMTP_USER + SMTP_PASS (a Google App Password). Falls back
     to this only if RESEND_API_KEY is absent.

Recipient defaults to Subidh's address; override with NOTIFY_EMAIL.
"""

import os
import json

DEFAULT_RECIPIENT = "subidhkhanal38@gmail.com"


def _recipient():
    return (os.environ.get("NOTIFY_EMAIL") or DEFAULT_RECIPIENT).strip()


def _send_via_resend(to_addr, subject, body_text):
    """Return True if Resend accepted the message."""
    import requests

    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key:
        return None  # not configured — let caller try the next backend
    sender = os.environ.get("NOTIFY_EMAIL_FROM", "onboarding@resend.dev").strip()
    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "from": sender,
                "to": [to_addr],
                "subject": subject,
                "text": body_text,
            }),
            timeout=15,
        )
        if resp.status_code in (200, 201):
            print(f"Email sent to {to_addr} via Resend.")
            return True
        print(f"Resend send failed ({resp.status_code}): {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"Resend send error: {e}")
        return False


def _send_via_smtp(to_addr, subject, body_text):
    """Return True if Gmail SMTP accepted the message."""
    import smtplib
    from email.message import EmailMessage

    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASS", "").strip()
    if not user or not password:
        return None  # not configured
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg.set_content(body_text)
    try:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls()
            s.login(user, password)
            s.send_message(msg)
        print(f"Email sent to {to_addr} via SMTP ({host}).")
        return True
    except Exception as e:
        print(f"SMTP send error: {e}")
        return False


def send_email(subject, body_text, to_addr=None):
    """Send the run summary by email. No-ops (prints a notice) when no email
    backend is configured, so it never breaks a run. Returns True on success."""
    to_addr = to_addr or _recipient()

    result = _send_via_resend(to_addr, subject, body_text)
    if result is True:
        return True
    if result is None:  # Resend not configured — try SMTP
        result = _send_via_smtp(to_addr, subject, body_text)
        if result is True:
            return True
        if result is None:
            print("Email not configured (set RESEND_API_KEY or SMTP_USER/"
                  "SMTP_PASS) — skipping email notification.")
            return False
    return False
