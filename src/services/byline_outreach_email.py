from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from uuid import UUID

from pydantic import EmailStr, TypeAdapter, ValidationError

from src.core.config import settings
from src.db.mongo import get_database
from src.services.apify_scrape import BYLINE_COLLECTION

logger = logging.getLogger(__name__)

_email_adapter = TypeAdapter(EmailStr)


def _valid_recipient_email(raw: str | None) -> str | None:
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s or s.lower() in {"not found", "n/a", "none", "nil"}:
        return None
    try:
        return str(_email_adapter.validate_python(s))
    except ValidationError:
        return None


def _split_subject_and_body(content: str) -> tuple[str, str]:
    text = (content or "").strip()
    if not text:
        return "Introduction", ""
    lower = text.lower()
    if lower.startswith("subject:"):
        first_line, _, remainder = text.partition("\n")
        subject_part = first_line.split(":", 1)[1].strip() if ":" in first_line else "Introduction"
        body = remainder.strip()
        return (subject_part or "Introduction"), body
    return "Introduction", text


def send_byline_outreach_emails(user_id: UUID) -> dict[str, int]:
    """
    For bylines with status False and an LLM response object, send outreach when
    llm_response.email is a valid address. Uses the user's `email` from Mongo as From.
    Attaches the configured resume PDF. Sets status True after a successful send, or when
    there is no recipient (nothing to send).
    """
    database = get_database()
    users_col = database["users"]
    col = database[BYLINE_COLLECTION]
    user_id_str = str(user_id)

    user = users_col.find_one({"user_id": user_id_str})
    if user is None:
        logger.error("send_byline_outreach_emails: user not found user_id=%s", user_id_str)
        return {"sent": 0, "skipped_no_recipient": 0, "failed": 0, "skipped_no_user": 1}

    sender = (user.get("email") or "").strip()
    if not sender:
        logger.error("send_byline_outreach_emails: user has no email user_id=%s", user_id_str)
        return {"sent": 0, "skipped_no_recipient": 0, "failed": 0, "skipped_no_user": 1}

    resume_path = Path(settings.resume_attachment_path).expanduser()
    if not resume_path.is_file():
        logger.error("Resume attachment missing at path=%s", resume_path)

    cursor = col.find(
        {
            "user_id": user_id_str,
            "status": False,
            "llm_response.email": {"$exists": True},
        }
    )

    sent = 0
    skipped_no_recipient = 0
    failed = 0

    smtp_ready = bool(
        settings.smtp_host and settings.smtp_username and settings.smtp_password,
    )

    for doc in cursor:
        doc_id = doc.get("_id")
        if doc_id is None:
            continue

        llm = doc.get("llm_response")
        if not isinstance(llm, dict):
            continue

        raw_email_field = (llm.get("email") or "").strip()
        is_dm_channel = raw_email_field.lower() == "linkedin dm"
        recipient = None if is_dm_channel else _valid_recipient_email(raw_email_field)
        content = llm.get("content") if isinstance(llm.get("content"), str) else ""
        subject, body = _split_subject_and_body(content)
        body_plain = (body or content or "").strip()
        signoff = f"\n\nRegards,\n{settings.email_signoff_name}"
        full_body = (body_plain + signoff).strip()

        if is_dm_channel:
            col.update_one(
                {"_id": doc_id, "status": False},
                {
                    "$set": {
                        "status": True,
                        "email_skip_reason": "linkedin_dm_channel",
                        "email_processed_at": datetime.now(timezone.utc),
                    }
                },
            )
            skipped_no_recipient += 1
            continue

        if recipient is None:
            col.update_one(
                {"_id": doc_id, "status": False},
                {
                    "$set": {
                        "status": True,
                        "email_skip_reason": "no_valid_recipient_email",
                        "email_processed_at": datetime.now(timezone.utc),
                    }
                },
            )
            skipped_no_recipient += 1
            continue

        if not smtp_ready:
            logger.warning("SMTP not configured; cannot send to=%s", recipient)
            col.update_one(
                {"_id": doc_id, "status": False},
                {
                    "$set": {
                        "email_last_error": "SMTP is not configured (SMTP_HOST, SMTP_USER_HARSH, SMTP_PASSWORD_HARSH).",
                    }
                },
            )
            failed += 1
            continue

        if not resume_path.is_file():
            col.update_one(
                {"_id": doc_id, "status": False},
                {
                    "$set": {
                        "email_last_error": f"Resume file not found: {resume_path}",
                    }
                },
            )
            failed += 1
            continue

        try:
            _send_smtp_email(
                sender_email=sender,
                to_addrs=[recipient],
                subject=subject,
                body=full_body,
                attachment_path=resume_path,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("SMTP send failed byline_id=%s to=%s", doc_id, recipient)
            col.update_one(
                {"_id": doc_id, "status": False},
                {"$set": {"email_last_error": str(exc)}},
            )
            failed += 1
            continue

        col.update_one(
            {"_id": doc_id, "status": False},
            {
                "$set": {
                    "status": True,
                    "email_sent_at": datetime.now(timezone.utc),
                    "email_to": recipient,
                    "email_last_error": None,
                }
            },
        )
        sent += 1
        logger.info("Outreach email sent byline_id=%s to=%s", doc_id, recipient)

    return {
        "sent": sent,
        "skipped_no_recipient": skipped_no_recipient,
        "failed": failed,
        "skipped_no_user": 0,
    }


def _send_smtp_email(
    *,
    sender_email: str,
    to_addrs: list[str],
    subject: str,
    body: str,
    attachment_path: Path,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject[:998]
    msg["From"] = sender_email
    msg["To"] = ", ".join(to_addrs)
    msg.set_content(body if body else "(No body.)")

    pdf_bytes = attachment_path.read_bytes()
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=attachment_path.name,
    )

    host = settings.smtp_host or ""
    port = int(settings.smtp_port)
    timeout = 60

    with smtplib.SMTP(host=host, port=port, timeout=timeout) as server:
        if settings.smtp_use_tls:
            server.starttls()
        user = settings.smtp_username or ""
        password = settings.smtp_password or ""
        server.login(user, password)
        server.send_message(msg)


def send_outreach_email_standalone(
    *,
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    attachment_path: str | Path,
) -> None:
    """
    Standalone helper for sending one MIME email with a PDF attachment using global SMTP settings.
    """
    path = Path(attachment_path).expanduser()
    if not path.is_file():
        msg = f"Attachment not found: {path}"
        raise FileNotFoundError(msg)
    if not (settings.smtp_host and settings.smtp_username and settings.smtp_password):
        msg = "SMTP is not fully configured (SMTP_HOST, SMTP_USER_HARSH, SMTP_PASSWORD_HARSH)."
        raise RuntimeError(msg)
    _send_smtp_email(
        sender_email=from_email,
        to_addrs=[to_email],
        subject=subject,
        body=body,
        attachment_path=path,
    )
