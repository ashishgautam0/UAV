from fastapi import APIRouter

from tracker import (
    get_cold_dm_todos,
    get_post_connection_follow_ups_due,
    get_hr_email_todos,
    get_platform_effectiveness,
    get_role_analysis,
    get_stats,
    get_status_funnel,
    get_weekly_trend,
)

router = APIRouter()


@router.get("/dashboard")
def dashboard_stats():
    return get_stats()


@router.get("/follow-ups")
def follow_ups():
    """Due follow-ups, each marked with whether it is actually sendable.

    A follow-up needs both halves: a written draft and an address to send it
    to. Dashboard hides the ones missing either rather than offering a card
    that cannot be acted on.
    """
    from tracker import get_cached_research, get_follow_up_draft

    df = get_post_connection_follow_ups_due()
    if df.empty:
        return []
    rows = df.astype(object).where(df.notna(), None).to_dict("records")

    recipients = {}
    for row in rows:
        company = row.get("company") or ""
        if company not in recipients:
            try:
                cached = get_cached_research(company) or {}
                recipients[company] = (cached.get("hiring_email") or "").strip()
            except Exception:
                recipients[company] = ""
        try:
            draft = get_follow_up_draft(row["id"]) or {}
        except Exception:
            draft = {}
        row["recipient"] = recipients[company] or None
        row["draft_ready"] = draft.get("status") == "ready" and bool(
            (draft.get("content") or "").strip())
    return rows


@router.get("/cold-dm-todos")
def cold_dm_todos():
    # The dashboard only needs the latest persisted PDF profile version; avoid
    # a private Storage list call on every Dashboard refresh.
    from profile import get_latest_profile_snapshot
    resume = get_latest_profile_snapshot()
    return get_cold_dm_todos((resume or {}).get("version"))


@router.get("/hr-email-todos")
def hr_email_todos():
    df = get_hr_email_todos()
    return df.astype(object).where(df.notna(), None).to_dict("records") if not df.empty else []


@router.get("/weekly-trend")
def weekly_trend():
    df = get_weekly_trend()
    return df.to_dict("records") if not df.empty else []


@router.get("/platform-effectiveness")
def platform_effectiveness():
    df = get_platform_effectiveness()
    return df.to_dict("records") if not df.empty else []


@router.get("/status-funnel")
def status_funnel():
    return get_status_funnel()


@router.get("/role-analysis")
def role_analysis():
    df = get_role_analysis()
    return df.to_dict("records") if not df.empty else []
