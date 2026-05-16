from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pymongo.errors import DuplicateKeyError

from db.mongo import get_database
from schemas.user import UserCreate, UserSchema

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserSchema])
def list_users() -> list[UserSchema]:
    database = get_database()
    users_collection = database["users"]
    docs = users_collection.find().sort("username", 1)
    result: list[UserSchema] = []
    for doc in docs:
        if not (doc.get("user_id") and doc.get("username") and doc.get("email")):
            continue
        result.append(
            UserSchema(
                user_id=UUID(str(doc["user_id"])),
                username=doc["username"],
                email=doc["email"],
            )
        )
    return result


@router.post("", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate) -> UserSchema:
    database = get_database()
    users_collection = database["users"]

    user_document = {
        "user_id": str(uuid4()),
        "username": payload.username,
        "email": str(payload.email),
    }

    try:
        users_collection.insert_one(user_document)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        ) from exc

    return UserSchema(**user_document)
