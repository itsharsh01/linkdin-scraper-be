from __future__ import annotations

import logging
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)

_SEND_TOOLBAR_PATTERN = re.compile(
    r'<div[^>]*id="send-toolbar"[^>]*>.*?</div>\s*',
    re.DOTALL | re.IGNORECASE,
)
_SCRIPT_PATTERN = re.compile(r"<script\b[^>]*>.*?</script>\s*", re.DOTALL | re.IGNORECASE)


def resolve_email_template_path() -> Path:
    configured = (getattr(settings, "email_template_path", None) or "").strip()
    if configured:
        path = Path(configured).expanduser()
    else:
        path = Path(__file__).resolve().parents[1] / "email-template.html"
    if not path.is_file():
        msg = f"Email template not found at {path}"
        raise FileNotFoundError(msg)
    return path


def load_email_template_html(*, strip_toolbar: bool = True) -> str:
    html = resolve_email_template_path().read_text(encoding="utf-8")
    if strip_toolbar:
        html = _SEND_TOOLBAR_PATTERN.sub("", html, count=1)
        html = _SCRIPT_PATTERN.sub("", html, count=1)
    return html


def _sender_email() -> str:
    sender = (settings.smtp_username or "").strip()
    if not sender:
        msg = "SMTP_USER_HARSH is not configured."
        raise RuntimeError(msg)
    return sender


def send_template_html_email(
    *,
    to_email: str,
    subject: str,
    attach_resume: bool = True,
    html_override: str | None = None,
) -> None:
    if not (settings.smtp_host and settings.smtp_username and settings.smtp_password):
        msg = "SMTP is not fully configured (SMTP_HOST, SMTP_USER_HARSH, SMTP_PASSWORD_HARSH)."
        raise RuntimeError(msg)

    html_body = html_override if html_override is not None else load_email_template_html()
    plain_fallback = (
        f"{settings.email_signoff_name} – AI/ML Engineer\n\n"
        "View this message in an HTML-capable email client for the full portfolio layout."
    )

    msg = EmailMessage()
    msg["Subject"] = subject[:998]
    msg["From"] = _sender_email()
    msg["To"] = to_email
    msg.set_content(plain_fallback)
    msg.add_alternative(html_body, subtype="html")

    if attach_resume:
        resume_path = Path(settings.resume_attachment_path).expanduser()
        if not resume_path.is_file():
            msg = f"Resume file not found: {resume_path}"
            raise FileNotFoundError(msg)
        msg.add_attachment(
            resume_path.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=resume_path.name,
        )

    host = settings.smtp_host or ""
    port = int(settings.smtp_port)

    with smtplib.SMTP(host=host, port=port, timeout=60) as server:
        if settings.smtp_use_tls:
            server.starttls()
        server.login(settings.smtp_username or "", settings.smtp_password or "")
        server.send_message(msg)

    logger.info("Template HTML email sent to=%s", to_email)
