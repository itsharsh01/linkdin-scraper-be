"""Regex-based email extraction from post text (before LLM)."""

from __future__ import annotations

import re

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

_DM_PATTERN = re.compile(
    r"\b("
    r"dm\s+me|send\s+(?:me\s+)?a\s+dm|message\s+me|reach\s+out|drop\s+a\s+message|"
    r"connect\s+with\s+me|send\s+your\s+resume|apply\s+via\s+linkedin|comment\s+below"
    r")\b",
    re.IGNORECASE,
)


def extract_emails(text: str | None) -> list[str]:
    """Return unique emails found in text, in order of appearance."""
    if not text:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for match in _EMAIL_PATTERN.findall(text):
        key = match.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(match)
    return ordered


def resolve_contact_for_outreach(text: str | None) -> tuple[list[str], str]:
    """
    Detect contact from post text without LLM.

    Returns (all_emails, outreach_value) where outreach_value is:
    - first email if any found
    - "LinkedIn DM" if DM-style CTA and no email
    - "" if nothing detected
    """
    emails = extract_emails(text)
    if emails:
        return emails, emails[0]
    if text and _DM_PATTERN.search(text):
        return [], "LinkedIn DM"
    return [], ""
