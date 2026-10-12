"""Shared logging configuration.

Call get_logger(name) from any module to obtain a named logger that writes
to both the terminal and the log file defined in src/config.LOG_FILE.
The root handler is configured once; subsequent calls are no-ops.
"""

import logging
import os

from src.config import LOG_FILE

_configured = False


def get_logger(name: str) -> logging.Logger:
    global _configured
    if not _configured:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

        fmt = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(fmt)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(fmt)

        root = logging.getLogger("review")
        root.setLevel(logging.INFO)
        root.addHandler(file_handler)
        root.addHandler(console_handler)

        _configured = True

    return logging.getLogger(f"review.{name}")
