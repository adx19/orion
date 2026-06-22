from playwright.sync_api import sync_playwright, Playwright
from utils.logger import logger

class mouse_events:

  def scrollDown(page):

    logger.info("Scrolling down...")
    page.mouse.wheel(0, 500)
    page.wait_for_timeout(1000)
  
  def scrollUp(page):

    logger.info("Scrolling up...")
    page.mouse.wheel(0, -500)
    page.wait_for_timeout(1000)
  
  def click(page, x, y):
    logger.info(f"Clicking at x={x}, y = {y}...")
    page.mouse.click(x, y)
    page.wait_for_timeout(1000)
  
  def double_click(page, x, y):
    logger.info(f"Double clicking at x={x} , y={y}...")
    page.mouse.dblclick(x,y)
    page.wait_for_timeout(1000)
    