"""
agent/response_parser.py

Parses and validates the raw text returned by Gemini into a structured
AgentAction dict. Handles markdown code fences and missing / extra keys.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from utils.logger import logger

# Typed alias for the parsed action
AgentAction = Dict[str, Any]

# Known valid action types
_VALID_ACTIONS = {"fill_form", "scroll", "click", "task_complete"}


class InvalidResponseError(Exception):
    """Raised when Gemini's response cannot be parsed into a valid AgentAction."""


def parse(raw_response: str) -> AgentAction:
    """
    Extract and validate the JSON AgentAction from *raw_response*.

    Gemini sometimes wraps JSON in markdown code fences (```json … ```)
    or returns extra prose — this function strips that noise first.

    Raises:
        InvalidResponseError: if the JSON is malformed or missing required keys.
    """
    logger.info("Parsing Gemini response")

    cleaned = _strip_code_fences(raw_response)

    try:
        data: AgentAction = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise InvalidResponseError(
            f"Gemini response is not valid JSON.\n"
            f"Raw response:\n{raw_response}\n"
            f"Error: {exc}"
        ) from exc

    _validate(data)

    action = data.get("action", "unknown")
    logger.info(f"Gemini selected action: '{action}'")
    if "thought" in data:
        logger.info(f"Gemini thought: {data['thought']}")

    return data


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if present."""
    # Match ```json ... ``` or ``` ... ```
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def _validate(data: AgentAction) -> None:
    """Raise InvalidResponseError if *data* is missing required keys."""
    if "action" not in data:
        raise InvalidResponseError(
            f"Gemini response missing 'action' key. Got: {data}"
        )

    action = data["action"]
    if action not in _VALID_ACTIONS:
        raise InvalidResponseError(
            f"Unknown action '{action}'. Expected one of: {_VALID_ACTIONS}"
        )

    if action == "fill_form":
        if "fields" not in data or not isinstance(data["fields"], dict):
            raise InvalidResponseError(
                "Action 'fill_form' requires a 'fields' dict. Got: {data}"
            )
        if not data["fields"]:
            raise InvalidResponseError(
                "Action 'fill_form' has an empty 'fields' dict."
            )

    if action == "scroll" and "direction" not in data:
        raise InvalidResponseError(
            "Action 'scroll' requires a 'direction' key ('up' or 'down')."
        )

    if action == "click" and ("x" not in data or "y" not in data):
        raise InvalidResponseError(
            "Action 'click' requires 'x' and 'y' coordinates."
        )
