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
