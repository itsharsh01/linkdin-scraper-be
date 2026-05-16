from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=1)
    email: EmailStr


class UserSchema(UserCreate):
    user_id: UUID
