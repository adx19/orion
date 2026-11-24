"""
agent/browser_tools.py

Standalone, reusable Playwright browser tool functions.
No hardcoded selectors — every interaction is driven by parameters.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Tuple

from playwright.sync_api import Browser, Page, Playwright

from config import settings
from utils.logger import logger


# ── Browser lifecycle ─────────────────────────────────────────────────────────

def open_browser(url: str, playwright: Playwright) -> Tuple[Page, Browser]:
    """Launch Chromium, open a new page, and navigate to *url*."""
    browser = playwright.chromium.launch(headless=False)
    logger.info("Browser launched")
    try:
        page = browser.new_page()
        navigate_to_url(page, url)
    except Exception:
        # The caller never receives the browser on failure, so close it here
        browser.close()
        raise
    return page, browser


def navigate_to_url(page: Page, url: str) -> None:
    """Navigate to *url* and wait until the network is idle."""
    logger.info(f"Navigating to URL: {url}")
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)


def close_browser(browser: Browser) -> None:
    """Close the browser gracefully."""
    logger.info("Closing browser")
    browser.close()


# ── Screenshots ───────────────────────────────────────────────────────────────

def take_screenshot(page: Page, name: str) -> str:
    """Capture a full-page screenshot and return the saved file path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = str(settings.SCREENSHOTS_DIR / f"{name}_{timestamp}.png")
    logger.info(f"Screenshot captured → {path}")
    page.screenshot(path=path, full_page=True)
    return path


# ── Mouse / keyboard interactions ─────────────────────────────────────────────

def click_on_screen(page: Page, x: float, y: float) -> None:
    """Click at absolute viewport coordinates (x, y)."""
    logger.info(f"Clicking at ({x}, {y})")
    page.mouse.click(x, y)
    page.wait_for_timeout(500)


def double_click(page: Page, x: float, y: float) -> None:
    """Double-click at absolute viewport coordinates (x, y)."""
    logger.info(f"Double-clicking at ({x}, {y})")
    page.mouse.dblclick(x, y)
    page.wait_for_timeout(500)


def scroll(page: Page, delta_y: int = 400) -> None:
    """Scroll the page vertically by *delta_y* pixels (negative = up)."""
    direction = "down" if delta_y > 0 else "up"
    logger.info(f"Scrolling {direction} by {abs(delta_y)}px")
    page.mouse.wheel(0, delta_y)
    page.wait_for_timeout(800)


def send_keys(page: Page, selector: str, text: str) -> None:
    """Focus *selector* and type *text* character by character."""
    logger.info(f"Sending keys to '{selector}'")
    page.locator(selector).fill(text)
    page.wait_for_timeout(300)


# ── Form helpers ──────────────────────────────────────────────────────────────

def fill_field_by_label(page: Page, label: str, value: str) -> bool:
    """
    Find an input/textarea associated with a <label> whose text contains
    *label* (case-insensitive) and fill it with *value*.

    Returns True on success, False if the field was not found.
    """
    logger.info(f"Filling form field '{label}' with value: '{value}'")
    try:
        # Playwright's get_by_label does fuzzy matching by default
        field = page.get_by_label(label, exact=False)
        if field.count() == 0:
            logger.warning(f"No field found for label: '{label}'")
            return False
        field.first.fill(value)
        page.wait_for_timeout(300)
        logger.info(f"Field '{label}' filled successfully")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to fill field '{label}': {exc}")
        return False
