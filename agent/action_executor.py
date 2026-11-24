"""
agent/action_executor.py

Dispatches an AgentAction (parsed from Gemini's response) to the
appropriate browser_tools function.

Supports the full general-purpose action set:
  click, type, press_enter, scroll, navigate, fill_form, done
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from agent import browser_tools
from agent.response_parser import AgentAction, click_coordinates, click_target
from utils.logger import logger

if TYPE_CHECKING:
    from playwright.sync_api import Page


# Result statuses returned by execute()
CONTINUE = "continue"  # action succeeded, keep going
FAILED = "failed"      # action failed, keep going (message says why)
DONE = "done"          # task complete, stop the loop


@dataclass
class ActionResult:
    """Outcome of one action: a status plus a human-readable message."""

    status: str
    message: str

    @property
    def ok(self) -> bool:
        return self.status != FAILED


def _ok(message: str) -> ActionResult:
    return ActionResult(CONTINUE, message)


def _fail(message: str) -> ActionResult:
    logger.warning(message)
    return ActionResult(FAILED, message)


def execute(action: AgentAction, page: "Page") -> ActionResult:
    """
    Execute *action* against *page*.

    Returns an ActionResult whose status is:
        DONE     – the agent loop should stop (task complete)
        CONTINUE – the action succeeded; the loop should continue
        FAILED   – the action failed; ``message`` explains why
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
        return ActionResult(DONE, str(reason))

    return _fail(f"Unknown action type '{action_type}' — skipped")


# ── Action handlers ───────────────────────────────────────────────────────────

def _click(action: AgentAction, page: "Page") -> ActionResult:
    """Click an element by visible text/target description or by x,y coordinates."""
    target = click_target(action)

    if target is not None:
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
                    return _ok(f"Clicked '{target}'")

            logger.warning(f"Could not find element with target='{target}' — trying text search")
            # Fallback: JavaScript click on element containing the text
            found = page.evaluate(f"""() => {{
                const els = [...document.querySelectorAll('a, button, [role=button], [role=link], input[type=submit]')];
                const match = els.find(e => e.innerText && e.innerText.toLowerCase().includes({repr(target.lower())}));
                if (match) match.click();
                return !!match;
            }}""")
            if not found:
                return _fail(f"Click failed: no clickable element matching '{target}' was found")
            page.wait_for_timeout(1500)
            return _ok(f"Clicked '{target}' via JavaScript fallback")
        except Exception as exc:  # noqa: BLE001
            return _fail(f"Click on '{target}' failed: {exc}")

    # No usable target: require explicit coordinates — never default to (0, 0)
    coords = click_coordinates(action)
    if coords is None:
        return _fail(
            "Click rejected: 'target' is empty and no valid 'x'/'y' coordinates were given"
        )
    x, y = coords
    logger.info(f"Clicking at coordinates ({x}, {y})")
    try:
        browser_tools.click_on_screen(page, x, y)
    except Exception as exc:  # noqa: BLE001
        return _fail(f"Click at ({x}, {y}) failed: {exc}")
    return _ok(f"Clicked at ({x}, {y})")


def _type(action: AgentAction, page: "Page") -> ActionResult:
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
                return _ok(f"Typed '{text}' into '{target}'")

        # Fallback: first visible input
        logger.warning(f"Could not find input '{target}' — typing into first visible input")
        found = page.evaluate(f"""() => {{
            const inputs = [...document.querySelectorAll('input[type=text], input[type=search], textarea, [role=searchbox]')];
            const visible = inputs.find(el => el.getBoundingClientRect().width > 0);
            if (visible) {{ visible.focus(); visible.value = {repr(text)}; visible.dispatchEvent(new Event('input', {{bubbles: true}})); }}
            return !!visible;
        }}""")
        if not found:
            return _fail(f"Type failed: no input matching '{target}' and no visible text input on the page")
        page.wait_for_timeout(500)
        return _ok(f"Input '{target}' not found; typed '{text}' into the first visible text input instead")
    except Exception as exc:  # noqa: BLE001
        return _fail(f"Type into '{target}' failed: {exc}")


def _press_enter(page: "Page") -> ActionResult:
    """Press Enter on the currently focused element."""
    logger.info("Pressing Enter")
    try:
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)
    except Exception as exc:  # noqa: BLE001
        return _fail(f"Press Enter failed: {exc}")
    return _ok("Pressed Enter")


def _scroll(action: AgentAction, page: "Page") -> ActionResult:
    direction = action.get("direction", "down")
    delta = 600 if direction == "down" else -600
    browser_tools.scroll(page, delta)
    return _ok(f"Scrolled {'down' if delta > 0 else 'up'}")


def _navigate(action: AgentAction, page: "Page") -> ActionResult:
    """Navigate directly to a URL."""
    url: str = action.get("url", "")
    if not url:
        return _fail("Navigate failed: action is missing a 'url'")
    logger.info(f"Navigating to: {url}")
    try:
        browser_tools.navigate_to_url(page, url)
    except Exception as exc:  # noqa: BLE001
        return _fail(f"Navigate to {url} failed: {exc}")
    return _ok(f"Navigated to {url}")


def _fill_form(action: AgentAction, page: "Page") -> ActionResult:
    """Fill each field specified in action['fields'] (legacy / explicit form tasks)."""
    fields: dict[str, str] = action.get("fields", {})
    logger.info(f"Filling form — {len(fields)} field(s): {list(fields.keys())}")

    missing = [
        label for label, value in fields.items()
        if not browser_tools.fill_field_by_label(page, label, value)
    ]

    if not missing:
        browser_tools.take_screenshot(page, "form_filled")
        _try_submit(page)
        browser_tools.take_screenshot(page, "after_submit")
        return ActionResult(DONE, f"Filled {len(fields)} field(s) and attempted submit")

    filled = [label for label in fields if label not in missing]
    return _fail(
        f"Fill form incomplete: could not find field(s) {missing}"
        + (f"; filled {filled}" if filled else "")
        + ". They may be off-screen or labelled differently."
    )


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
