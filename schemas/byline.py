from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class BylineListItem(BaseModel):
    id: str
    user_id: str
    source_url: str | None = None
    created_at: datetime | None = None
    text: str | None = None
    url: str | None = None
    author_profile_url: str | None = Field(default=None, serialization_alias="authorProfileUrl")
    author_name: str | None = Field(default=None, serialization_alias="authorName")
    status: bool | None = None
    email_skip_reason: str | None = None
    llm_response: dict[str, Any] | None = None

    model_config = {"populate_by_name": True}


class BylineListResponse(BaseModel):
    user_id: UUID
    date: str
    count: int
    items: list[BylineListItem]
