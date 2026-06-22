"""
main.py — Orion entry point

Usage:
    python main.py

Requirements:
    1. pip install -r requirements.txt
    2. playwright install
    3. Create a .env file and set GEMINI_API_KEY=your_key
"""

from agent.browserAgent import BrowserAgent

if __name__ == "__main__":
    agent = BrowserAgent()
    agent.run()