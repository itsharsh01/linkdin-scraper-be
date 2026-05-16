from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from db.mongo import get_database
from services.apify_scrape import BYLINE_COLLECTION
from utils.email_extract import resolve_contact_for_outreach
from utils.linkedin_match_parse import parse_job_match_llm_output
from utils.llm_fallback import generate_llm_text

logger = logging.getLogger(__name__)

RESUME_SKILLS_BLOCK = """- 3 years production engineering | IIT Gandhinagar PGD-AI/ML (2026)
- LangGraph, LangChain, LlamaIndex, RAG pipelines, RAGAS evaluation, LangSmith
- Multi-agent systems, CrewAI, AutoGen, tool calling, agent memory design
- Fine-tuning LLMs,  Knowledge Graphs,  Page Indexes
- FastAPI, NestJS, Python, TypeScript, PostgreSQL, Redis, Docker, Kubernetes, GCP/AWS"""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_linkedin_job_match_prompt(post_text: str) -> str:
    post = (post_text or "").strip() or "(No post text.)"
    return f"""LinkedIn Post:
\"\"\"
{post}
\"\"\"

My Resume & Skills:
{RESUME_SKILLS_BLOCK}

Instructions:
1. Extract the key job requirements from the post.
2. Score the match between the JD and my skills (0–100) with a one-line reason.
3. If score ≥ 60, write a short professional cold email / LinkedIn message (max 120 words) that:
   - Opens with the specific role/company
   - Highlights 2–3 directly relevant skills/projects
   - Mentions fine-tuning, knowledge graphs, and page indexes naturally if relevant
   - Ends with: "Resume attached for your reference." when writing a formal email
   - Has a compelling subject line

Output format:
Match Score: [ X ]

Reason of score: [ One line ]

Subject: [subject line]

[email / DM body].
"""


def _safe_parse_llm_output(raw: str) -> dict[str, Any]:
    try:
        return parse_job_match_llm_output(raw)
    except Exception:
        logger.exception("Failed to parse LLM output; using fallback structure.")
        return {
            "score": None,
            "reason": "",
            "email": "",
            "content": (raw or "")[:12000],
        }


def process_pending_bylines_with_llm(user_id: UUID) -> dict[str, int]:
    """
    For bylines with status False and no LLM payload yet (llm_response null), run LLM and
    persist llm_response. Does not change status (remains False until outreach email succeeds).
    """
    database = get_database()
    col = database[BYLINE_COLLECTION]
    user_id_str = str(user_id)

    cursor = col.find({"user_id": user_id_str, "status": False, "llm_response": None})
    processed = 0
    failed = 0

    for doc in cursor:
        doc_id = doc.get("_id")
        if doc_id is None:
            continue

        post_text = doc.get("text")
        if not (isinstance(post_text, str) and post_text.strip()):
            col.update_one(
                {"_id": doc_id, "status": False},
                {
                    "$set": {
                        "detected_emails": [],
                        "detected_email": None,
                        "llm_response": {
                            "score": None,
                            "reason": "No post text to analyze.",
                            "email": "",
                            "content": "",
                        },
                        "status": False,
                        "llm_processed_at": _utcnow(),
                        "llm_last_error": None,
                    }
                },
            )
            processed += 1
            continue

        detected_emails, outreach_email = resolve_contact_for_outreach(post_text)
        col.update_one(
            {"_id": doc_id, "status": False},
            {
                "$set": {
                    "detected_emails": detected_emails,
                    "detected_email": detected_emails[0] if detected_emails else None,
                    "email_detected_at": _utcnow(),
                }
            },
        )

        prompt = build_linkedin_job_match_prompt(post_text)

        try:
            raw = generate_llm_text(prompt, max_output_tokens=4096)
        except Exception as exc:  # noqa: BLE001
            logger.exception("LLM call failed for byline_id=%s", doc_id)
            col.update_one(
                {"_id": doc_id, "status": False},
                {"$set": {"llm_last_error": str(exc), "llm_attempt_at": _utcnow()}},
            )
            failed += 1
            continue

        parsed = _safe_parse_llm_output(raw)
        llm_response = {
            "score": parsed.get("score"),
            "reason": parsed.get("reason") or "",
            "email": outreach_email,
            "content": parsed.get("content") or "",
        }

        col.update_one(
            {"_id": doc_id, "status": False},
            {
                "$set": {
                    "llm_response": llm_response,
                    "detected_emails": detected_emails,
                    "detected_email": detected_emails[0] if detected_emails else None,
                    "status": False,
                    "llm_processed_at": _utcnow(),
                    "llm_last_error": None,
                }
            },
        )
        processed += 1

    return {"processed": processed, "failed": failed}
