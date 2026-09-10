import re

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response

from ..models.schemas import Prep28Request, Prep28Response
from prep28 import (
    get_prep28,
    upsert_prep28,
    upload_prep_pdf,
    get_prep_pdf,
    list_prep_pdf_ids,
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
    """Task ids (Block B) that currently have an uploaded PDF."""
    return {"task_ids": list_prep_pdf_ids(_DEFAULT_USERNAME)}


@router.post("/pdf/{task_id}")
async def upload_pdf(task_id: str, request: Request):
    """Upload/replace a Block-B task's PDF. Body is the raw PDF bytes."""
    if not _TASK_ID_RE.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task id")
    data = await request.body()
    if not data or data[:5] != b"%PDF-":
        raise HTTPException(status_code=400, detail="Not a PDF file")
    if len(data) > _MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="PDF too large (max 20 MB)")
    try:
        upload_prep_pdf(task_id, data, _DEFAULT_USERNAME)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    return {"ok": True, "task_id": task_id}


@router.get("/pdf/{task_id}")
def view_pdf(task_id: str):
    """Stream the PDF inline (served from our origin so it embeds in an
    iframe and reads in-app without downloading)."""
    if not _TASK_ID_RE.match(task_id):
        raise HTTPException(status_code=404, detail="Not found")
    data = get_prep_pdf(task_id, _DEFAULT_USERNAME)
    if not data:
        raise HTTPException(status_code=404, detail="No PDF for this task")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{task_id}.pdf"',
            "Cache-Control": "private, max-age=60",
        },
    )


@router.delete("/pdf/{task_id}")
def remove_pdf(task_id: str):
    if not _TASK_ID_RE.match(task_id):
        raise HTTPException(status_code=404, detail="Not found")
    delete_prep_pdf(task_id, _DEFAULT_USERNAME)
    return {"ok": True}
