"""
agent/context_collector.py

Gathers the current page state and packages it as a structured dict
that the prompt builder can convert into a Gemini prompt.
Collects inputs, buttons, links, and visible text — not just form labels.
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
        text_content    – trimmed visible text (first 4000 chars)
        inputs          – list of visible input field descriptions
        buttons         – list of visible button texts
        links           – list of visible link texts
        screenshot_path – path to the latest screenshot (or None)
    """
    logger.info("Collecting page context")

    url: str = page.url
    title: str = page.title()

    # Visible text — trim to avoid bloating the prompt
    raw_text: str = page.evaluate("() => document.body.innerText") or ""
    text_content: str = raw_text.strip()[:4000]

    # Collect interactive elements
    inputs: List[str] = _collect_inputs(page)
    buttons: List[str] = _collect_buttons(page)
    links: List[str] = _collect_links(page)

    # Capture a fresh screenshot if none supplied
    if screenshot_path is None:
        screenshot_path = browser_tools.take_screenshot(page, "context")

    ctx: PageContext = {
        "task": task,
        "url": url,
        "title": title,
        "text_content": text_content,
        "inputs": inputs,
        "buttons": buttons,
        "links": links,
        "screenshot_path": screenshot_path,
    }

    logger.info(
        f"Context collected — URL: {url} | Title: {title} | "
        f"Inputs: {len(inputs)} | Buttons: {len(buttons)} | Links: {len(links)}"
    )
    return ctx


def _collect_inputs(page: Page) -> List[str]:
    """Return descriptions of visible input fields (type, placeholder, aria-label, name)."""
    try:
        return page.evaluate("""() => {
            const results = [];
            const inputs = document.querySelectorAll('input:not([type=hidden]), textarea, [role=searchbox], [role=textbox], [contenteditable=true]');
            for (const el of inputs) {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) continue;
                const parts = [];
                const type = el.getAttribute('type') || el.tagName.toLowerCase();
                if (type && type !== 'text') parts.push(type);
                const placeholder = el.getAttribute('placeholder');
                if (placeholder) parts.push(`placeholder="${placeholder}"`);
                const ariaLabel = el.getAttribute('aria-label');
                if (ariaLabel) parts.push(`aria-label="${ariaLabel}"`);
                const name = el.getAttribute('name');
                if (name) parts.push(`name="${name}"`);
                const id = el.getAttribute('id');
                if (id) parts.push(`id="${id}"`);
                if (parts.length === 0) parts.push('input');
                results.push(parts.join(', '));
            }
            return results;
        }""")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Could not collect inputs: {exc}")
        return []


def _collect_buttons(page: Page) -> List[str]:
    """Return visible button texts."""
    try:
        return page.evaluate("""() => {
            const results = [];
            const btns = document.querySelectorAll('button, [role=button], input[type=submit], input[type=button]');
            for (const el of btns) {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) continue;
                const text = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim();
                if (text && text.length < 100) results.push(text);
            }
            return [...new Set(results)].slice(0, 30);
        }""")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Could not collect buttons: {exc}")
        return []


def _collect_links(page: Page) -> List[str]:
    """Return visible link texts (top 30 non-empty)."""
    try:
        return page.evaluate("""() => {
            const results = [];
            const anchors = document.querySelectorAll('a[href]');
            for (const el of anchors) {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) continue;
                const text = (el.innerText || el.getAttribute('aria-label') || '').trim();
                if (text && text.length < 120) results.push(text);
            }
            return [...new Set(results)].slice(0, 30);
        }""")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Could not collect links: {exc}")
        return []
