"""
agent/context_collector.py

Gathers the current page state and packages it as a structured dict
that the prompt builder can convert into a Gemini prompt.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from playwright.sync_api import Page

from agent import browser_tools
from utils.logger import logger

PageContext = Dict[str, Any]


def collect(page: Page, task: str, screenshot_path: Optional[str] = None) -> PageContext:
    """
    Collect the current page context needed by the Gemini agent.

    Returns a dict with:
        task            – the overall task the agent is trying to complete
        url             – current page URL
        title           – document title
        text_content    – trimmed visible text (first 4000 chars to stay within prompt budget)
        form_labels     – list of visible <label> texts on the page
        screenshot_path – path to the latest screenshot (or None)
    """
    logger.info("Collecting page context")

    url: str = page.url
    title: str = page.title()

    # Visible text — trim to avoid bloating the prompt
    raw_text: str = page.evaluate("() => document.body.innerText") or ""
    text_content: str = raw_text.strip()[:4000]

    # All visible label texts
    form_labels: List[str] = _collect_labels(page)

    # Capture a fresh screenshot if none supplied
    if screenshot_path is None:
        screenshot_path = browser_tools.take_screenshot(page, "context")

    ctx: PageContext = {
        "task": task,
        "url": url,
        "title": title,
        "text_content": text_content,
        "form_labels": form_labels,
        "screenshot_path": screenshot_path,
    }

    logger.info(
        f"Context collected — URL: {url} | Title: {title} | "
        f"Labels found: {len(form_labels)}"
    )
    return ctx


def _collect_labels(page: Page) -> List[str]:
    """Return a deduplicated list of visible <label> inner texts."""
    try:
        labels = page.locator("label").all_inner_texts()
        # Strip whitespace, drop empties, deduplicate while preserving order
        seen: set[str] = set()
        result: List[str] = []
        for lbl in labels:
            clean = lbl.strip()
            if clean and clean not in seen:
                seen.add(clean)
                result.append(clean)
        return result
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Could not collect form labels: {exc}")
        return []
