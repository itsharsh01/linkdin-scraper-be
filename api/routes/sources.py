from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pymongo.errors import DuplicateKeyError

from db.mongo import get_database
from schemas.source import SourceCreate, SourceSchema

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("", response_model=SourceSchema, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreate) -> SourceSchema:
    database = get_database()
    users_collection = database["users"]
    sources_collection = database["sources"]

    if users_collection.find_one({"user_id": str(payload.user_id)}) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found for the provided user_id.",
        )

    source_document = {
        "id": str(uuid4()),
        "user_id": str(payload.user_id),
        "url": str(payload.url),
    }

    try:
        sources_collection.insert_one(source_document)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A source with this id already exists.",
        ) from exc

    return SourceSchema(**source_document)
