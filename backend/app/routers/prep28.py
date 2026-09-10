import re

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response

from ..models.schemas import Prep28Request, Prep28Response
from prep28 import (
    get_prep28,
    upsert_prep28,
    upload_prep_pdf,
    get_prep_pdf,
    list_task_pdfs,
    list_all_prep_pdfs,
    delete_prep_pdf,
)

router = APIRouter()

_DEFAULT_USERNAME = "subidh"

# Only Block-B tasks may have study PDFs: id shape is "<day>-b-<index>".
_TASK_ID_RE = re.compile(r"^\d{1,2}-b-\d{1,2}$")
_MAX_PDF_BYTES = 20 * 1024 * 1024  # 20 MB


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


@router.post("/pdf/{task_id}")
async def upload_pdf(task_id: str, request: Request, name: str = ""):
    """Upload a named PDF under a Block-B task. Body is the raw PDF bytes and
    the display filename is passed as ?name=."""
    if not _TASK_ID_RE.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task id")
    if not name.strip():
        raise HTTPException(status_code=400, detail="Missing file name")
    data = await request.body()
    if not data or data[:5] != b"%PDF-":
        raise HTTPException(status_code=400, detail="Not a PDF file")
    if len(data) > _MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="PDF too large (max 20 MB)")
    try:
        stored = upload_prep_pdf(task_id, name, data, _DEFAULT_USERNAME)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    return {"ok": True, "task_id": task_id, "name": stored}


@router.get("/pdf/{task_id}/{filename}")
def view_pdf(task_id: str, filename: str):
    """Stream one named PDF inline (served from our origin so it opens in a new
    browser tab)."""
    if not _TASK_ID_RE.match(task_id):
        raise HTTPException(status_code=404, detail="Not found")
    data = get_prep_pdf(task_id, filename, _DEFAULT_USERNAME)
    if not data:
        raise HTTPException(status_code=404, detail="No such PDF")
    safe = filename.replace('"', "")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{safe}"',
            "Cache-Control": "private, max-age=60",
        },
    )


@router.delete("/pdf/{task_id}/{filename}")
def remove_pdf(task_id: str, filename: str):
    if not _TASK_ID_RE.match(task_id):
        raise HTTPException(status_code=404, detail="Not found")
    delete_prep_pdf(task_id, filename, _DEFAULT_USERNAME)
    return {"ok": True}
