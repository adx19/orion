"""
agent/browserAgent.py

Orchestrates the full Gemini-powered agent loop:

  Task
    → Open browser & navigate
    → Collect page context
    → Build Gemini prompt
    → Send to Gemini
    → Parse response
    → Execute action
    → Repeat until task_complete or max iterations reached
    → Close browser
"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

from agent import action_executor, browser_tools, context_collector, gemini_client, prompt_builder
from agent.response_parser import InvalidResponseError, parse as parse_response
from config import settings
from utils.logger import logger


class BrowserAgent:
    """Gemini-powered autonomous browser agent."""

    def run(self, task: str | None = None, url: str | None = None) -> None:
        """
        Execute the agent loop for the given *task* on *url*.

        Args:
            task: A plain-English description of what the agent should do.
                  Defaults to the standard form-filling task if not provided.
            url:  The website to open. Defaults to settings.TARGET_URL.
        """
        if url is None:
            url = settings.TARGET_URL

        if task is None:
            task = "Explore the page and describe what you see."

        logger.info("=" * 60)
        logger.info("Orion Agent starting")
        logger.info(f"Target URL : {url}")
        logger.info(f"Task       : {task}")
        logger.info(f"Max steps  : {settings.MAX_ITERATIONS}")
        logger.info("=" * 60)

        with sync_playwright() as playwright:
            page, browser = browser_tools.open_browser(url, playwright)

            # Initial screenshot
            screenshot_path = browser_tools.take_screenshot(page, "initial")

            try:
                self._agent_loop(page, task, screenshot_path)
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Agent loop terminated with an error: {exc}")
                browser_tools.take_screenshot(page, "error_state")
            finally:
                browser_tools.close_browser(browser)

        logger.info("=" * 60)
        logger.info("Orion Agent finished")
        logger.info("=" * 60)

    # ── Internal loop ─────────────────────────────────────────────────────────

    def _agent_loop(self, page, task: str, initial_screenshot: str) -> None:
        screenshot_path = initial_screenshot

        for iteration in range(1, settings.MAX_ITERATIONS + 1):
            logger.info(f"--- Agent iteration {iteration}/{settings.MAX_ITERATIONS} ---")

            # 1. Collect page context
            ctx = context_collector.collect(page, task, screenshot_path)

            # 2. Build prompt
            prompt = prompt_builder.build(ctx)

            # 3. Ask Gemini
            try:
                raw_response = gemini_client.send_prompt(prompt)
            except gemini_client.GeminiError as exc:
                logger.error(f"Gemini API failure: {exc}")
                break

            # 4. Parse Gemini's response
            try:
                agent_action = parse_response(raw_response)
            except InvalidResponseError as exc:
                logger.error(f"Failed to parse Gemini response: {exc}")
                # Take a screenshot of the current state and try again
                screenshot_path = browser_tools.take_screenshot(page, f"parse_error_{iteration}")
                continue

            # 5. Execute the action
            result = action_executor.execute(agent_action, page)

            # 6. Capture updated state
            screenshot_path = browser_tools.take_screenshot(page, f"step_{iteration}")

            if result == action_executor.DONE:
                logger.success("Agent completed the task successfully!")  # type: ignore[attr-defined]
                return

        logger.warning(
            f"Agent reached the maximum iteration limit ({settings.MAX_ITERATIONS}) "
            "without completing the task."
        )