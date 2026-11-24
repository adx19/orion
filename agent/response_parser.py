"""
agent/response_parser.py

Parses and validates the raw text returned by Gemini into a structured
AgentAction dict. Handles markdown code fences and missing / extra keys.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple

from utils.logger import logger

# Typed alias for the parsed action
AgentAction = Dict[str, Any]

# Known valid action types
_VALID_ACTIONS = {
    "click",
    "type",
    "press_enter",
    "scroll",
    "navigate",
    "fill_form",
    "done",
    "task_complete",  # legacy alias for done
}


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


def click_target(data: AgentAction) -> Optional[str]:
    """Return the click target if it is a non-empty string, else None."""
    target = data.get("target")
    if isinstance(target, str) and target.strip():
        return target.strip()
    return None


def click_coordinates(data: AgentAction) -> Optional[Tuple[float, float]]:
    """Return (x, y) if both are present, numeric and non-negative, else None."""
    coords = []
    for key in ("x", "y"):
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            return None
        coords.append(float(value))
    return coords[0], coords[1]


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

    # click: requires a non-empty 'target' string OR numeric 'x' and 'y'
    if action == "click":
        if click_target(data) is None and click_coordinates(data) is None:
            raise InvalidResponseError(
                "Action 'click' requires a non-empty 'target' string or numeric "
                f"'x'/'y' coordinates. Got target={data.get('target')!r}, "
                f"x={data.get('x')!r}, y={data.get('y')!r}."
            )

    # type: requires 'target' input description and 'text' to type
    if action == "type":
        if "text" not in data:
            raise InvalidResponseError(
                "Action 'type' requires a 'text' key with the string to type."
            )

    # scroll: requires direction
    if action == "scroll" and "direction" not in data:
        raise InvalidResponseError(
            "Action 'scroll' requires a 'direction' key ('up' or 'down')."
        )

    # navigate: requires url
    if action == "navigate" and "url" not in data:
        raise InvalidResponseError(
            "Action 'navigate' requires a 'url' key."
        )

    # fill_form: requires non-empty fields dict
    if action == "fill_form":
        if "fields" not in data or not isinstance(data["fields"], dict):
            raise InvalidResponseError(
                f"Action 'fill_form' requires a 'fields' dict. Got: {data}"
            )
        if not data["fields"]:
            raise InvalidResponseError(
                "Action 'fill_form' has an empty 'fields' dict."
            )
