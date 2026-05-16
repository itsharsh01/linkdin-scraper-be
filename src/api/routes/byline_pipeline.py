from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.db.mongo import get_database
from src.schemas.pipeline import EmailBatchResponse, LlmBatchResponse
from src.services.byline_outreach_email import send_byline_outreach_emails
from src.services.linkedin_post_llm_pipeline import process_pending_bylines_with_llm

router = APIRouter(prefix="/users", tags=["byline-pipeline"])


def _ensure_user_exists(user_id: UUID) -> None:
    database = get_database()
    if database["users"].find_one({"user_id": str(user_id)}) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found for the provided user_id.",
        )


@router.post(
    "/{user_id}/bylines/llm-process",
    response_model=LlmBatchResponse,
    status_code=status.HTTP_200_OK,
)
def run_llm_on_pending_bylines(user_id: UUID) -> LlmBatchResponse:
    """
    Manual run of the same LLM step as the scheduler (after scrape): processes bylines with
    `status=False` and `llm_response=null`. Does not set status True; use send-emails next.
    """
    _ensure_user_exists(user_id)
    try:
        stats = process_pending_bylines_with_llm(user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM batch failed: {exc}",
        ) from exc
    return LlmBatchResponse(user_id=user_id, **stats)


@router.post(
    "/{user_id}/bylines/send-emails",
    response_model=EmailBatchResponse,
    status_code=status.HTTP_200_OK,
)
def run_outreach_emails_for_bylines(user_id: UUID) -> EmailBatchResponse:
    """
    Manual run of the same outreach email step as the scheduler: bylines with `status=False`
    and an LLM payload. Sends when `llm_response.email` is valid; sets `status=True` after send
    or when there is no recipient.
    """
    _ensure_user_exists(user_id)
    try:
        stats = send_byline_outreach_emails(user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email batch failed: {exc}",
        ) from exc
    if stats.get("skipped_no_user"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found for the provided user_id.",
        )
    return EmailBatchResponse(
        user_id=user_id,
        sent=stats["sent"],
        skipped_no_recipient=stats["skipped_no_recipient"],
        failed=stats["failed"],
    )
