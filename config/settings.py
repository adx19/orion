"""
config/settings.py

Loads environment variables from .env and exposes typed configuration
for the entire Orion agent. No API key should ever be hardcoded here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Locate and load .env ─────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _ROOT / ".env"

load_dotenv(dotenv_path=_ENV_PATH)

# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-")

if not GEMINI_API_KEY:
    raise EnvironmentError(
        "\n[ERROR] GEMINI_API_KEY is not set.\n"
        f"  → Create a file at: {_ENV_PATH}\n"
        "  → Add the line:  GEMINI_API_KEY=your_key_here\n"
    )

# ── Target ────────────────────────────────────────────────────────────────────
TARGET_URL: str = os.getenv(
    "TARGET_URL",
    "https://ui.shadcn.com/docs/forms/react-hook-form",
)

# ── Agent behaviour ───────────────────────────────────────────────────────────
MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "10"))
GEMINI_RETRY_ATTEMPTS: int = int(os.getenv("GEMINI_RETRY_ATTEMPTS", "3"))

# ── Paths ─────────────────────────────────────────────────────────────────────
SCREENSHOTS_DIR: Path = _ROOT / "screenshots"
LOGS_DIR: Path = _ROOT / "logs"

SCREENSHOTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
