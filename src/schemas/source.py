from uuid import UUID

from pydantic import BaseModel, HttpUrl


class SourceCreate(BaseModel):
    user_id: UUID
    url: HttpUrl


class SourceSchema(SourceCreate):
    id: str
    url: HttpUrl
