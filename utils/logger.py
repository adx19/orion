"""
utils/logger.py

Configures the shared 'Orion' logger with:
  - File handler  → logs/automation.log
  - Console handler → stdout with colour-coded levels
  - Custom SUCCESS level (between INFO and WARNING)
"""

import logging
import sys
from pathlib import Path

# ── Ensure logs directory exists ──────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)

# ── Custom SUCCESS level ──────────────────────────────────────────────────────
SUCCESS_LEVEL = 25  # between INFO (20) and WARNING (30)
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")


def _success(self, message, *args, **kwargs):  # noqa: ANN001
    if self.isEnabledFor(SUCCESS_LEVEL):
        self._log(SUCCESS_LEVEL, message, args, **kwargs)


logging.Logger.success = _success  # type: ignore[attr-defined]

# ── Build logger ──────────────────────────────────────────────────────────────
logger = logging.getLogger("Orion")

if not logger.handlers:
    logger.setLevel(logging.DEBUG)

    _fmt = logging.Formatter("[%(levelname)s] %(message)s")
    _detailed_fmt = logging.Formatter(
        "%(asctime)s | [%(levelname)s] | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    _console = logging.StreamHandler(sys.stdout)
    _console.setLevel(logging.DEBUG)
    _console.setFormatter(_fmt)
    logger.addHandler(_console)

    # File handler
    _file = logging.FileHandler("logs/automation.log", encoding="utf-8")
    _file.setLevel(logging.DEBUG)
    _file.setFormatter(_detailed_fmt)
    logger.addHandler(_file)