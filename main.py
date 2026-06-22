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


def _prompt(label: str, default: str = "") -> str:
    """Print a styled prompt and return stripped user input."""
    suffix = f" [{default}]" if default else ""
    value = input(f"\n  {label}{suffix}: ").strip()
    return value if value else default


if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  🚀  Orion Browser Agent")
    print("=" * 55)

    url = _prompt(
        "Target URL",
        default="https://",
    )
    if not url or url == "https://":
        print("[ERROR] A valid URL is required. Exiting.")
        raise SystemExit(1)

    task = _prompt("Task (what should the agent do on that page)")
    if not task:
        print("[ERROR] A task description is required. Exiting.")
        raise SystemExit(1)

    print()
    agent = BrowserAgent()
    agent.run(url=url, task=task)