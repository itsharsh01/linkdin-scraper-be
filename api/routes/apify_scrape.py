from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from schemas.apify_scrape import ApifyScrapeRequest, ApifyScrapeResponse
from services.apify_scrape import run_apify_scrape_for_user

router = APIRouter(prefix="/users", tags=["linkedin-apify-scrape"])


@router.post(
    "/{user_id}/linkedin-apify-scrape",
    response_model=ApifyScrapeResponse,
    status_code=status.HTTP_200_OK,
)
def scrape_linkedin_via_apify(user_id: UUID, payload: ApifyScrapeRequest) -> ApifyScrapeResponse:
    """
    For each saved source URL for the user, run the LinkedIn Apify actor sequentially
    (one URL per run). Raw Apify items are stored as flexible documents; an **AuthorByline**
    digest (text, url, authorProfileUrl, authorName) is stored per item.
    """
    try:
        return run_apify_scrape_for_user(
            user_id=user_id,
            max_sources=payload.max_sources,
            limit_per_source=payload.limit_per_source,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
