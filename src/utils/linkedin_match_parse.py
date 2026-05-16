"""
Parse job-match style LLM output into a stable JSON-friendly dict.

Expected sections (flexible spacing / optional brackets):
Match Score, Reason of score, Email, Subject, body.
"""

from __future__ import annotations

import re
from typing import Any


def parse_job_match_llm_output(raw: str) -> dict[str, Any]:
    """
    Always returns keys: score (int | None), reason, email, content (str).
    `content` holds subject + body when possible; otherwise best-effort remainder.
    """
    text = (raw or "").strip()
    out: dict[str, Any] = {"score": None, "reason": "", "email": "", "content": ""}
    if not text:
        return out

    score_m = re.search(r"Match\s*Score:\s*\[?\s*(\d{1,3})\s*\]?", text, re.IGNORECASE)
    if score_m:
        try:
            val = int(score_m.group(1))
            out["score"] = max(0, min(100, val))
        except ValueError:
            out["score"] = None

    reason_m = re.search(r"Reason\s+of\s+score:\s*\[?\s*([^\n]+?)\s*\]?", text, re.IGNORECASE)
    if reason_m:
        out["reason"] = _clean_line(reason_m.group(1))

    email_m = re.search(r"Email:\s*\[?\s*([^\]\n]+?)\s*\]?", text, re.IGNORECASE)
    if email_m:
        out["email"] = _clean_line(email_m.group(1))
        if out["email"].lower() in {"not found", "n/a", "none", "nil", ""}:
            out["email"] = ""
        # Keep "LinkedIn DM" as-is — it signals a DM channel, not a missing address

    subj_m = re.search(r"(?im)^Subject:\s*(.+)$", text)
    subject = _clean_line(subj_m.group(1)) if subj_m else ""

    # Body: lines after Subject block until end, excluding leading label lines we already parsed
    body_text = text
    if subj_m:
        after = text[subj_m.end() :].strip()
        body_text = after

    body_text = re.sub(r"(?im)^Match\s*Score:.*$", "", body_text)
    body_text = re.sub(r"(?im)^Reason\s+of\s+score:.*$", "", body_text)
    body_text = re.sub(r"(?im)^Email:.*$", "", body_text)
    body_text = re.sub(r"(?im)^Subject:.*$", "", body_text)
    body_text = body_text.strip()

    if subject and body_text:
        out["content"] = f"Subject: {subject}\n\n{body_text}".strip()
    elif subject:
        out["content"] = f"Subject: {subject}".strip()
    else:
        out["content"] = body_text or text

    if not out["reason"]:
        out["reason"] = _fallback_reason(text)
    if not out["content"]:
        out["content"] = text

    return out


def _clean_line(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _fallback_reason(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines:
        if re.match(r"^Match\s*Score:", ln, re.I):
            continue
        if re.match(r"^Reason\s+of\s+score:", ln, re.I):
            return _clean_line(re.sub(r"^Reason\s+of\s+score:\s*", "", ln, flags=re.I))
    return ""
