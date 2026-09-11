import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from ..models.schemas import Prep28Request, Prep28Response
from prep28 import (
    get_prep28,
    upsert_prep28,
    create_pdf_upload_url,
    create_pdf_view_url,
    list_all_prep_pdfs,
    delete_prep_pdf,
)

router = APIRouter()

_DEFAULT_USERNAME = "subidh"

# Only Block-B tasks may have study PDFs: id shape is "<day>-b-<index>".
_TASK_ID_RE = re.compile(r"^\d{1,2}-b-\d{1,2}$")


@router.get("", response_model=Prep28Response)
def read_prep28():
    state = get_prep28(_DEFAULT_USERNAME)
    return Prep28Response(**(state or {}))


@router.put("", response_model=Prep28Response)
def update_prep28(body: Prep28Request):
    # Store the whole state blob (dumped as plain JSON-safe dict).
    state = body.model_dump()
    saved = upsert_prep28(_DEFAULT_USERNAME, state)
    return Prep28Response(**(saved or {}))


# ---- Block-B study PDFs ----

@router.get("/pdfs")
def list_pdfs():
    """Map of Block-B task id -> [filenames] for every task that has PDFs."""
    return {"pdfs": list_all_prep_pdfs(_DEFAULT_USERNAME)}


@router.post("/pdf-url/{task_id}")
def upload_pdf_url(task_id: str, name: str = ""):
    """Hand the browser a signed URL so it can upload the PDF straight to
    storage. The bytes never pass through this function — the platform caps
    request bodies at ~4.5 MB, which is smaller than a real study PDF."""
    if not _TASK_ID_RE.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task id")
    if not name.strip():
        raise HTTPException(status_code=400, detail="Missing file name")
    try:
        return create_pdf_upload_url(task_id, name, _DEFAULT_USERNAME)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not start upload: {e}")


@router.get("/pdf/{task_id}/{filename}")
def view_pdf(task_id: str, filename: str):
    """Redirect to a short-lived signed URL for the PDF. Redirecting (rather
    than streaming the bytes) keeps large PDFs under the platform's response
    size cap and still gives the UI one stable link to point at."""
    if not _TASK_ID_RE.match(task_id):
        raise HTTPException(status_code=404, detail="Not found")
    try:
        url = create_pdf_view_url(task_id, filename, _DEFAULT_USERNAME)
    except Exception:
        url = None
    if not url:
        raise HTTPException(status_code=404, detail="No such PDF")
    return RedirectResponse(url, status_code=307)


@router.delete("/pdf/{task_id}/{filename}")
def remove_pdf(task_id: str, filename: str):
    if not _TASK_ID_RE.match(task_id):
        raise HTTPException(status_code=404, detail="Not found")
    delete_prep_pdf(task_id, filename, _DEFAULT_USERNAME)
    return {"ok": True}
