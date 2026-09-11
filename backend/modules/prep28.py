"""
28-day prep progress data layer — stores and retrieves the user's prep28
progress (start date, day override, checked task ids) from Supabase.

The plan CONTENT is static in the frontend; this module only persists the
mutable per-user state as a single jsonb blob so the shape can evolve without
a schema migration.
"""

import os
from datetime import datetime

_supabase_client = None


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


def get_prep28(username="subidh"):
    """Get the stored prep28 state dict. Returns {} if none saved yet."""
    try:
        db = _get_client()
        result = (
            db.table("prep28_progress")
            .select("state")
            .eq("username", username)
            .execute()
        )
        if result.data:
            return result.data[0].get("state") or {}
    except Exception as e:
        print(f"[prep28] get_prep28 failed: {e}")
    return {}


def upsert_prep28(username="subidh", state=None):
    """Create or update the prep28 state. Returns the saved state dict."""
    if state is None:
        state = {}
    db = _get_client()
    payload = {
        "username": username,
        "state": state,
        "updated_at": datetime.now().isoformat(),
    }
    result = db.table("prep28_progress").upsert(
        payload, on_conflict="username"
    ).execute()
    if result.data:
        return result.data[0].get("state") or {}
    return state


# ===================== BLOCK-B STUDY PDFs (Supabase Storage) =====================
# Per Block-B task, the user can upload one or more PDFs and open each in a new
# tab. Stored privately in the "prep28-pdfs" bucket, one folder per task:
#   "<username>/<task_id>/<safe filename>.pdf"
# The real filename is preserved so the app can show it and open a link to it.

import re

_PDF_BUCKET = "prep28-pdfs"


def _safe_name(filename):
    """Sanitize an uploaded filename into a safe storage key.

    Strips any path components, keeps a conservative character set, guarantees a
    ".pdf" extension, and caps the length so it fits comfortably as a key.
    """
    name = str(filename or "").replace("\\", "/").split("/")[-1].strip()
    name = re.sub(r"[^A-Za-z0-9._() -]", "_", name)
    name = name.lstrip(".") or "document"
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    if len(name) > 120:
        name = name[-120:]
    return name


def _task_dir(task_id, username="subidh"):
    return f"{username}/{task_id}"


def _pdf_path(task_id, filename, username="subidh"):
    return f"{_task_dir(task_id, username)}/{_safe_name(filename)}"


def _ensure_pdf_bucket(db):
    try:
        db.storage.create_bucket(_PDF_BUCKET, options={"public": False})
    except Exception:
        pass  # already exists — create is only needed once


def upload_prep_pdf(task_id, filename, data, username="subidh"):
    """Store (or replace) a named PDF under a Block-B task. Returns the stored
    (safe) filename."""
    db = _get_client()
    _ensure_pdf_bucket(db)
    safe = _safe_name(filename)
    db.storage.from_(_PDF_BUCKET).upload(
        _pdf_path(task_id, safe, username),
        data,
        {"content-type": "application/pdf", "upsert": "true"},
    )
    return safe


def create_pdf_upload_url(task_id, filename, username="subidh"):
    """Signed URL letting the browser upload straight to Supabase Storage.

    Uploads must NOT be proxied through the API: the serverless platform caps
    request bodies at ~4.5 MB and rejects anything larger with a 413 before our
    code runs, which is smaller than a real study PDF. The browser PUTs the
    bytes to this URL instead, so only the signed-URL request touches the API.
    """
    from storage3.types import CreateSignedUploadUrlOptions

    db = _get_client()
    _ensure_pdf_bucket(db)
    safe = _safe_name(filename)
    res = db.storage.from_(_PDF_BUCKET).create_signed_upload_url(
        _pdf_path(task_id, safe, username),
        CreateSignedUploadUrlOptions(upsert="true"),
    )
    return {"signed_url": res["signed_url"], "name": safe}


def create_pdf_view_url(task_id, filename, username="subidh", expires_in=3600):
    """Short-lived signed URL to read one PDF straight from Supabase Storage.

    Responses are size-capped on the serverless platform too, so the API
    redirects to this instead of streaming the bytes itself.
    """
    db = _get_client()
    res = db.storage.from_(_PDF_BUCKET).create_signed_url(
        _pdf_path(task_id, filename, username), expires_in
    )
    return res.get("signedURL") or res.get("signedUrl")


def get_prep_pdf(task_id, filename, username="subidh"):
    """Return the bytes for one named PDF under a task, or None."""
    try:
        db = _get_client()
        return db.storage.from_(_PDF_BUCKET).download(
            _pdf_path(task_id, filename, username)
        )
    except Exception:
        return None


def list_task_pdfs(task_id, username="subidh"):
    """Return the filenames of PDFs stored under a single task."""
    try:
        db = _get_client()
        items = db.storage.from_(_PDF_BUCKET).list(_task_dir(task_id, username))
        return sorted(
            it["name"]
            for it in items
            if isinstance(it, dict) and str(it.get("name", "")).endswith(".pdf")
        )
    except Exception as e:
        print(f"[prep28] list_task_pdfs failed: {e}")
        return []


def list_all_prep_pdfs(username="subidh"):
    """Return a mapping of task_id -> [filenames] for every task with PDFs."""
    try:
        db = _get_client()
        folders = db.storage.from_(_PDF_BUCKET).list(username)
        out = {}
        for f in folders:
            if not isinstance(f, dict):
                continue
            task_id = str(f.get("name", ""))
            # Folder entries have no file metadata (id is None for prefixes).
            if not task_id or task_id.endswith(".pdf"):
                continue
            names = list_task_pdfs(task_id, username)
            if names:
                out[task_id] = names
        return out
    except Exception as e:
        print(f"[prep28] list_all_prep_pdfs failed: {e}")
        return {}


def delete_prep_pdf(task_id, filename, username="subidh"):
    try:
        db = _get_client()
        db.storage.from_(_PDF_BUCKET).remove(
            [_pdf_path(task_id, filename, username)]
        )
        return True
    except Exception:
        return False
