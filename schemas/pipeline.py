from uuid import UUID

from pydantic import BaseModel, Field


class LlmBatchResponse(BaseModel):
    user_id: UUID
    processed: int = Field(description="Bylines that received an LLM result (or empty-post skip).")
    failed: int = Field(description="Bylines where the LLM call failed; status stays False for retry.")


class EmailBatchResponse(BaseModel):
    user_id: UUID
    sent: int
    skipped_no_recipient: int = Field(
        description="Marked complete (status True) because llm_response had no valid recipient email.",
    )
    failed: int = Field(description="Send or config errors; status stays False for retry.")
