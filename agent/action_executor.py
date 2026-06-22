"""
agent/action_executor.py

Dispatches an AgentAction (parsed from Gemini's response) to the
appropriate browser_tools function. All field names come from Gemini —
none are hardcoded here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent import browser_tools
from agent.response_parser import AgentAction
from utils.logger import logger

if TYPE_CHECKING:
    from playwright.sync_api import Page


# Returned by execute() to signal whether the agent loop should stop
CONTINUE = "continue"
DONE = "done"


def execute(action: AgentAction, page: "Page") -> str:
    """
    Execute *action* against *page*.

    Returns:
        DONE     – the agent loop should stop (task complete)
        CONTINUE – the agent loop should continue
    """
    action_type: str = action.get("action", "unknown")

    if action_type == "fill_form":
        return _fill_form(action, page)

    if action_type == "scroll":
        return _scroll(action, page)

    if action_type == "click":
        return _click(action, page)

    if action_type == "task_complete":
        logger.success("Task completed successfully!")  # type: ignore[attr-defined]
        return DONE

    logger.warning(f"Unknown action type received from Gemini: '{action_type}' — skipping")
    return CONTINUE


# ── Action handlers ───────────────────────────────────────────────────────────

def _fill_form(action: AgentAction, page: "Page") -> str:
    """Fill each field specified in action['fields']."""
    fields: dict[str, str] = action.get("fields", {})

    logger.info(f"Filling form — {len(fields)} field(s): {list(fields.keys())}")

    all_ok = True
    for label, value in fields.items():
        success = browser_tools.fill_field_by_label(page, label, value)
        if not success:
            logger.warning(f"Field '{label}' could not be filled — it may not be visible yet")
            all_ok = False

    if all_ok:
        # Take a confirmation screenshot after filling
        browser_tools.take_screenshot(page, "form_filled")

        # Submit the form — look for a Submit button
        _try_submit(page)

        browser_tools.take_screenshot(page, "after_submit")
        return DONE

    # If some fields were missing, scroll and retry next iteration
    logger.info("Not all fields were filled — scrolling to reveal more of the page")
    browser_tools.scroll(page, 400)
    return CONTINUE


def _scroll(action: AgentAction, page: "Page") -> str:
    direction = action.get("direction", "down")
    delta = 500 if direction == "down" else -500
    browser_tools.scroll(page, delta)
    return CONTINUE


def _click(action: AgentAction, page: "Page") -> str:
    x = float(action.get("x", 0))
    y = float(action.get("y", 0))
    browser_tools.click_on_screen(page, x, y)
    return CONTINUE


def _try_submit(page: "Page") -> None:
    """Attempt to click a Submit button; log a warning if not found."""
    try:
        submit_btn = page.get_by_role("button", name="Submit")
        if submit_btn.count() > 0:
            logger.info("Submitting form")
            submit_btn.first.click()
            page.wait_for_timeout(2000)
        else:
            logger.warning("No Submit button found — form may auto-submit or require manual action")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Submit attempt failed: {exc}")
