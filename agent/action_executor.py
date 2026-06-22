"""
agent/action_executor.py

Dispatches an AgentAction (parsed from Gemini's response) to the
appropriate browser_tools function.

Supports the full general-purpose action set:
  click, type, press_enter, scroll, navigate, fill_form, done
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

    if action_type == "click":
        return _click(action, page)

    if action_type == "type":
        return _type(action, page)

    if action_type == "press_enter":
        return _press_enter(page)

    if action_type == "scroll":
        return _scroll(action, page)

    if action_type == "navigate":
        return _navigate(action, page)

    if action_type == "fill_form":
        return _fill_form(action, page)

    if action_type in ("done", "task_complete"):
        reason = action.get("reason", action.get("thought", "Task complete."))
        logger.success(f"✅ Agent completed the task: {reason}")  # type: ignore[attr-defined]
        return DONE

    logger.warning(f"Unknown action type received from Gemini: '{action_type}' — skipping")
    return CONTINUE


# ── Action handlers ───────────────────────────────────────────────────────────

def _click(action: AgentAction, page: "Page") -> str:
    """Click an element by visible text/target description or by x,y coordinates."""
    target: str = action.get("target", "")

    if target:
        logger.info(f"Clicking element: '{target}'")
        try:
            # Try role=button first, then links, then any element with matching text
            for locator in [
                page.get_by_role("button", name=target, exact=False),
                page.get_by_role("link", name=target, exact=False),
                page.get_by_text(target, exact=False),
            ]:
                if locator.count() > 0:
                    locator.first.click()
                    page.wait_for_timeout(1500)
                    logger.info(f"Clicked '{target}' successfully")
                    return CONTINUE

            logger.warning(f"Could not find element with target='{target}' — trying text search")
            # Fallback: JavaScript click on element containing the text
            page.evaluate(f"""() => {{
                const els = [...document.querySelectorAll('a, button, [role=button], [role=link], input[type=submit]')];
                const match = els.find(e => e.innerText && e.innerText.toLowerCase().includes({repr(target.lower())}));
                if (match) match.click();
            }}""")
            page.wait_for_timeout(1500)
            return CONTINUE
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Click on '{target}' failed: {exc}")
            return CONTINUE

    # Fallback: coordinate click
    x = float(action.get("x", 0))
    y = float(action.get("y", 0))
    logger.info(f"Clicking at coordinates ({x}, {y})")
    browser_tools.click_on_screen(page, x, y)
    return CONTINUE


def _type(action: AgentAction, page: "Page") -> str:
    """Find an input by its target description and type text into it."""
    target: str = action.get("target", "")
    text: str = action.get("text", "")

    logger.info(f"Typing '{text}' into '{target}'")

    try:
        # Try by placeholder, aria-label, label text, then role
        for locator in [
            page.get_by_placeholder(target, exact=False),
            page.get_by_label(target, exact=False),
            page.get_by_role("searchbox"),
            page.get_by_role("textbox"),
        ]:
            if locator.count() > 0:
                locator.first.click()
                locator.first.fill(text)
                page.wait_for_timeout(500)
                logger.info(f"Typed '{text}' into '{target}' successfully")
                return CONTINUE

        # Fallback: first visible input
        logger.warning(f"Could not find input '{target}' — typing into first visible input")
        page.evaluate(f"""() => {{
            const inputs = [...document.querySelectorAll('input[type=text], input[type=search], textarea, [role=searchbox]')];
            const visible = inputs.find(el => el.getBoundingClientRect().width > 0);
            if (visible) {{ visible.focus(); visible.value = {repr(text)}; visible.dispatchEvent(new Event('input', {{bubbles: true}})); }}
        }}""")
        page.wait_for_timeout(500)
        return CONTINUE
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Type action failed: {exc}")
        return CONTINUE


def _press_enter(page: "Page") -> str:
    """Press Enter on the currently focused element."""
    logger.info("Pressing Enter")
    try:
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Press Enter failed: {exc}")
    return CONTINUE


def _scroll(action: AgentAction, page: "Page") -> str:
    direction = action.get("direction", "down")
    delta = 600 if direction == "down" else -600
    browser_tools.scroll(page, delta)
    return CONTINUE


def _navigate(action: AgentAction, page: "Page") -> str:
    """Navigate directly to a URL."""
    url: str = action.get("url", "")
    if not url:
        logger.warning("Navigate action missing 'url' key")
        return CONTINUE
    logger.info(f"Navigating to: {url}")
    browser_tools.navigate_to_url(page, url)
    return CONTINUE


def _fill_form(action: AgentAction, page: "Page") -> str:
    """Fill each field specified in action['fields'] (legacy / explicit form tasks)."""
    fields: dict[str, str] = action.get("fields", {})
    logger.info(f"Filling form — {len(fields)} field(s): {list(fields.keys())}")

    all_ok = True
    for label, value in fields.items():
        success = browser_tools.fill_field_by_label(page, label, value)
        if not success:
            logger.warning(f"Field '{label}' could not be filled — it may not be visible yet")
            all_ok = False

    if all_ok:
        browser_tools.take_screenshot(page, "form_filled")
        _try_submit(page)
        browser_tools.take_screenshot(page, "after_submit")
        return DONE

    logger.info("Not all fields were filled — scrolling to reveal more of the page")
    browser_tools.scroll(page, 400)
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
