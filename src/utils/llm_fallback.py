"""
Reusable multi-provider LLM text generation: Gemini → NVIDIA (OpenAI-compatible) → Groq.

Configure via environment (loaded in Settings): GOOGLE_API_KEY or GEMINI_API_KEY (google-genai SDK),
NVIDIA_API_KEY, GROQ_API_KEY. Optional model overrides: GEMINI_MODEL, NVIDIA_LLM_MODEL,
GROQ_LLM_MODEL.

Use from any service:

    from src.utils.llm_fallback import generate_llm_text

    text = generate_llm_text("Your prompt here")
"""

from __future__ import annotations

import logging
from typing import Callable

from src.core.config import settings

logger = logging.getLogger(__name__)


def _extract_gemini_text(response: object) -> str:
    try:
        t = getattr(response, "text", None)
        if isinstance(t, str) and t.strip():
            return t.strip()
    except Exception:  # noqa: BLE001 — blocked / no candidates
        pass
    parts: list[str] = []
    for cand in getattr(response, "candidates", None) or []:
        content = getattr(cand, "content", None)
        if content is None:
            continue
        for part in getattr(content, "parts", None) or []:
            ptext = getattr(part, "text", None)
            if isinstance(ptext, str) and ptext:
                parts.append(ptext)
    return "\n".join(parts).strip()


def _normalize_gemini_model_id(model: str) -> str:
    """google-genai expects e.g. gemini-2.5-flash, not models/gemini-2.5-flash."""
    m = (model or "gemini-2.5-flash").strip()
    if m.startswith("models/"):
        return m[len("models/") :]
    return m


def _call_gemini(prompt: str, max_output_tokens: int) -> str:
    from google import genai
    from google.genai import types

    key = settings.google_api_key
    if not key:
        msg = "No GOOGLE_API_KEY or GEMINI_API_KEY configured."
        raise RuntimeError(msg)

    client = genai.Client(api_key=key)
    model = _normalize_gemini_model_id(settings.gemini_model)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=max_output_tokens),
    )
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    return _extract_gemini_text(response)


def _call_nvidia(prompt: str, max_output_tokens: int) -> str:
    from openai import OpenAI

    key = settings.nvidia_api_key
    if not key:
        msg = "No NVIDIA_API_KEY configured."
        raise RuntimeError(msg)

    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=key)
    completion = client.chat.completions.create(
        model=settings.nvidia_llm_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_output_tokens,
        temperature=0.4,
    )
    choice = completion.choices[0] if completion.choices else None
    content = getattr(choice, "message", None)
    text = getattr(content, "content", None) if content is not None else None
    return (text or "").strip()


def _call_groq(prompt: str, max_output_tokens: int) -> str:
    from groq import Groq

    key = settings.groq_api_key
    if not key:
        msg = "No GROQ_API_KEY configured."
        raise RuntimeError(msg)

    client = Groq(api_key=key)
    completion = client.chat.completions.create(
        model=settings.groq_llm_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_output_tokens,
        temperature=0.4,
    )
    choice = completion.choices[0] if completion.choices else None
    content = getattr(choice, "message", None)
    text = getattr(content, "content", None) if content is not None else None
    return (text or "").strip()


def generate_llm_text(prompt: str, *, max_output_tokens: int = 4096) -> str:
    """
    Return non-empty model output, trying Gemini, then NVIDIA, then Groq.

    Raises RuntimeError if every configured provider fails or returns empty text.
    """
    providers: list[tuple[str, Callable[[str, int], str]]] = [
        ("gemini", _call_gemini),
        ("nvidia", _call_nvidia),
        ("groq", _call_groq),
    ]
    errors: list[str] = []

    for name, fn in providers:
        try:
            text = fn(prompt, max_output_tokens)
            if text:
                logger.info("LLM response from provider=%s chars=%s", name, len(text))
                return text
            errors.append(f"{name}: empty response")
        except Exception as exc:  # noqa: BLE001 — intentional fallback chain
            err = f"{name}: {type(exc).__name__}: {exc}"
            errors.append(err)
            logger.warning("LLM provider failed (%s); trying next if available.", err)

    raise RuntimeError("All LLM providers failed or returned empty: " + " | ".join(errors))
