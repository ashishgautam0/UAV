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
# Per Block-B task, the user can upload a PDF and read it inline in the app.
# Stored privately in the "prep28-pdfs" bucket at "<username>/<task_id>.pdf".

_PDF_BUCKET = "prep28-pdfs"


def _pdf_path(task_id, username="subidh"):
    return f"{username}/{task_id}.pdf"


def _ensure_pdf_bucket(db):
    try:
        db.storage.create_bucket(_PDF_BUCKET, options={"public": False})
    except Exception:
        pass  # already exists — create is only needed once


def upload_prep_pdf(task_id, data, username="subidh"):
    """Store (or replace) the PDF for a Block-B task. Returns True on success."""
    db = _get_client()
    _ensure_pdf_bucket(db)
    db.storage.from_(_PDF_BUCKET).upload(
        _pdf_path(task_id, username),
        data,
        {"content-type": "application/pdf", "upsert": "true"},
    )
    return True


def get_prep_pdf(task_id, username="subidh"):
    """Return the PDF bytes for a task, or None if none stored."""
    try:
        db = _get_client()
        return db.storage.from_(_PDF_BUCKET).download(_pdf_path(task_id, username))
    except Exception:
        return None


def list_prep_pdf_ids(username="subidh"):
    """Return the list of task ids that have an uploaded PDF."""
    try:
        db = _get_client()
        items = db.storage.from_(_PDF_BUCKET).list(username)
        return [
            it["name"][:-4]
            for it in items
            if isinstance(it, dict) and str(it.get("name", "")).endswith(".pdf")
        ]
    except Exception as e:
        print(f"[prep28] list_prep_pdf_ids failed: {e}")
        return []


def delete_prep_pdf(task_id, username="subidh"):
    try:
        db = _get_client()
        db.storage.from_(_PDF_BUCKET).remove([_pdf_path(task_id, username)])
        return True
    except Exception:
        return False
