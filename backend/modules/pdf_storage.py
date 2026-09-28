"""Supabase storage helpers for the application resume PDF.

These were extracted from the 28-day prep module when that feature was removed;
the resume upload had always shared its bucket and client.
"""

import os

_supabase_client = None

# The bucket keeps its original name. Renaming it here would not rename it in
# Supabase — it would point at a bucket that does not exist and orphan every
# resume PDF already uploaded.
_PDF_BUCKET = "prep28-pdfs"


def _get_client():
    """Return the Supabase client, creating it on first call."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    from supabase import create_client

    _url = os.environ.get("SUPABASE_URL", "")
    _key = os.environ.get("SUPABASE_KEY", "")

    if not _url or not _key:
        raise RuntimeError(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY."
        )

    _supabase_client = create_client(_url, _key)
    return _supabase_client


def _encode_url_path(url):
    """Percent-encode the path of a signed URL, leaving the query intact.

    The storage client builds the signed URL by concatenating the raw object
    key, so a filename containing a space yields a malformed URL that strict
    clients reject outright.
    """
    from urllib.parse import quote, urlsplit, urlunsplit

    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=quote(parts.path, safe="/%")))


def _ensure_pdf_bucket(db):
    try:
        db.storage.create_bucket(_PDF_BUCKET, options={"public": False})
    except Exception:
        pass  # already exists — create is only needed once
