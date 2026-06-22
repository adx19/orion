"""
agent/gemini_client.py

Thin wrapper around the Google Gen AI SDK.
Sends a prompt to Gemini and returns the raw response text.
Implements retry logic with exponential back-off.
"""

from __future__ import annotations

import time

import google.generativeai as genai

from config import settings
from utils.logger import logger


class GeminiError(Exception):
    """Raised when the Gemini API call fails after all retries."""


# Initialise the SDK once at module load time
genai.configure(api_key=settings.GEMINI_API_KEY)
_model = genai.GenerativeModel(model_name=settings.GEMINI_MODEL)


def send_prompt(prompt: str) -> str:
    """
    Send *prompt* to Gemini and return the response text.

    Retries up to ``settings.GEMINI_RETRY_ATTEMPTS`` times with
    exponential back-off on transient errors.

    Raises:
        GeminiError: if all retry attempts are exhausted.
    """
    logger.info("Sending context to Gemini")

    last_exc: Exception | None = None
    for attempt in range(1, settings.GEMINI_RETRY_ATTEMPTS + 1):
        try:
            response = _model.generate_content(prompt)
            text: str = response.text.strip()
            logger.info(f"Gemini responded (attempt {attempt})")
            return text
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            wait = 2 ** attempt
            logger.warning(
                f"Gemini API error on attempt {attempt}/{settings.GEMINI_RETRY_ATTEMPTS}: "
                f"{exc}. Retrying in {wait}s…"
            )
            time.sleep(wait)

    raise GeminiError(
        f"Gemini API failed after {settings.GEMINI_RETRY_ATTEMPTS} attempts: {last_exc}"
    )
