from fastapi import APIRouter

from ..models.schemas import Prep28Request, Prep28Response
from prep28 import get_prep28, upsert_prep28

router = APIRouter()

_DEFAULT_USERNAME = "subidh"


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
