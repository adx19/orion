"""
agent/gemini_client.py

Thin wrapper around the Google Gen AI SDK (``google-genai``).
Sends a prompt (plus an optional screenshot) to Gemini and returns the raw
response text. Implements retry logic with exponential back-off.
"""

from __future__ import annotations

import time
from pathlib import Path

from google import genai
from google.genai import types

from config import settings
from utils.logger import logger


class GeminiError(Exception):
    """Raised when the Gemini API call fails after all retries."""


# Initialise the client once at module load time
_client = genai.Client(api_key=settings.GEMINI_API_KEY)


def _image_part(image_path: str | None) -> types.Part | None:
    """Load *image_path* as a PNG image part, or return None if unavailable."""
    if not image_path:
        return None
    path = Path(image_path)
    if not path.is_file():
        logger.warning(f"Screenshot not found, sending text only: {image_path}")
        return None
    return types.Part.from_bytes(data=path.read_bytes(), mime_type="image/png")


def send_prompt(prompt: str, image_path: str | None = None) -> str:
    """
    Send *prompt* (and the screenshot at *image_path*, if given) to Gemini
    and return the response text.

    Retries up to ``settings.GEMINI_RETRY_ATTEMPTS`` times with
    exponential back-off on transient errors.

    Raises:
        GeminiError: if all retry attempts are exhausted.
    """
    contents: list = []
    image = _image_part(image_path)
    if image is not None:
        contents.append(image)
    contents.append(prompt)

    logger.info(
        "Sending context to Gemini"
        + (f" with screenshot {image_path}" if image is not None else " (text only)")
    )

    last_exc: Exception | None = None
    for attempt in range(1, settings.GEMINI_RETRY_ATTEMPTS + 1):
        try:
            response = _client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
            )
            if not response.text:
                raise GeminiError("Gemini returned an empty response")
            text: str = response.text.strip()
            logger.info(f"Gemini responded (attempt {attempt})")
            return text
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt == settings.GEMINI_RETRY_ATTEMPTS:
                break
            wait = 2 ** attempt
            logger.warning(
                f"Gemini API error on attempt {attempt}/{settings.GEMINI_RETRY_ATTEMPTS}: "
                f"{exc}. Retrying in {wait}s…"
            )
            time.sleep(wait)

    raise GeminiError(
        f"Gemini API failed after {settings.GEMINI_RETRY_ATTEMPTS} attempts: {last_exc}"
    )
