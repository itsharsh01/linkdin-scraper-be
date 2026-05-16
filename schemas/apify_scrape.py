from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from core.config import settings


class ApifyScrapeRequest(BaseModel):
    """Options for running the LinkedIn Apify actor against a user's saved sources."""

    max_sources: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of source URLs to run. Omit to process all sources for the user.",
    )
    limit_per_source: int = Field(
        default=settings.apify_limit_per_source,
        ge=1,
        le=500,
        description="Actor input limitPerSource (default from LIMIT_PER_SOURCE_HARSH in .env).",
    )


class AuthorByline(BaseModel):
    """Compact digest of a scraped item (matches the core fields used in scraped_items.json)."""

    text: str | None = None
    url: str | None = None
    authorProfileUrl: str | None = None
    authorName: str | None = None


class SourceScrapeOutcome(BaseModel):
    source_url: str
    raw_items_saved: int = 0
    author_bylines_saved: int = 0
    error: str | None = None


class ApifyScrapeResponse(BaseModel):
    user_id: UUID
    sources_planned: int
    sources_completed: int
    outcomes: list[SourceScrapeOutcome]
    author_bylines: list[AuthorByline]
    started_at: datetime
    finished_at: datetime
