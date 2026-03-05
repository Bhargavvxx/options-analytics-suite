"""
Structured logging configuration for the Option Analytics Suite.

Call ``setup_logging()`` once at startup.  Use ``get_logger(__name__)``
in every module to get a child logger that respects the global config.
"""
from __future__ import annotations

import logging
import sys
from typing import Optional

_INITIALISED = False


def setup_logging(
    level: str = "INFO",
    fmt: str = "%(asctime)s | %(name)-28s | %(levelname)-8s | %(message)s",
    stream: Optional[object] = None,
) -> None:
    """Initialise the root logger (idempotent)."""
    global _INITIALISED
    if _INITIALISED:
        return
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.addHandler(handler)
    _INITIALISED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.  Always call ``setup_logging()`` first."""
    return logging.getLogger(name)
