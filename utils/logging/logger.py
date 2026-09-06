"""
Central structured logger.

* One logger hierarchy rooted at ``cocacola`` - use :func:`get_logger`.
* Every record is enriched with runtime context (test, browser, device,
  environment, xdist worker) via :class:`ContextFilter`.
* Every message passes through :class:`MaskingFilter` so secrets never
  reach the console or log files.
* File handlers are attached per execution by :func:`attach_file_handler`
  (called from ``conftest.py`` once the execution directory exists).

Log line format::

    2026-09-06 02:35:41 | INFO     | LoginPage            | gw0 | test_login | Entering username
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

from utils.logging.masking import mask_text

ROOT_LOGGER_NAME = "cocacola"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-28s | %(worker)s | %(test)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Thread-local runtime context injected into every log record.
_context = threading.local()
_DEFAULT_CONTEXT: dict[str, str] = {
    "test": "-",
    "browser": "-",
    "device": "desktop",
    "environment": "-",
    "worker": os.getenv("PYTEST_XDIST_WORKER", "main"),
}


def set_log_context(**kwargs: Any) -> None:
    """Update the runtime context (test name, browser, device...)."""
    current = getattr(_context, "data", dict(_DEFAULT_CONTEXT))
    current.update({k: str(v) for k, v in kwargs.items() if v is not None})
    _context.data = current


def get_log_context() -> dict[str, str]:
    return dict(getattr(_context, "data", _DEFAULT_CONTEXT))


def clear_log_context() -> None:
    _context.data = dict(_DEFAULT_CONTEXT)


class ContextFilter(logging.Filter):
    """Injects test/browser/device/env/worker fields into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = get_log_context()
        for key, value in ctx.items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


class MaskingFilter(logging.Filter):
    """Masks secrets in the rendered message and its arguments."""

    def __init__(self, enabled: bool = True) -> None:
        super().__init__()
        self.enabled = enabled

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.enabled:
            return True
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - defensive
            return True
        record.msg = mask_text(message)
        record.args = ()
        return True


def _mask_enabled() -> bool:
    # Import lazily to avoid a config <-> logging import cycle at startup.
    try:
        from utils.config.config_reader import get_config

        return get_config().mask_secrets
    except Exception:
        return True


def _root() -> logging.Logger:
    return logging.getLogger(ROOT_LOGGER_NAME)


def configure_logging(level: str | int | None = None) -> logging.Logger:
    """Configure the console handler once. Safe to call repeatedly."""
    root = _root()
    if getattr(root, "_cocacola_configured", False):
        return root

    level_value: str | int = level if level is not None else os.getenv("LOG_LEVEL", "INFO")
    root.setLevel(level_value)
    root.propagate = False

    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    console.addFilter(ContextFilter())
    console.addFilter(MaskingFilter(enabled=_mask_enabled()))
    root.addHandler(console)

    root._cocacola_configured = True  # type: ignore[attr-defined]
    return root


def attach_file_handler(log_file: Path, name: str = "execution") -> logging.Handler:
    """Attach (or replace) a file handler writing to ``log_file``."""
    root = configure_logging()
    detach_file_handler(name)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.set_name(name)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    handler.addFilter(ContextFilter())
    handler.addFilter(MaskingFilter(enabled=_mask_enabled()))
    root.addHandler(handler)
    return handler


def detach_file_handler(name: str) -> None:
    root = _root()
    for handler in list(root.handlers):
        if handler.get_name() == name:
            handler.flush()
            handler.close()
            root.removeHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger, e.g. ``get_logger("LoginPage")``."""
    configure_logging()
    short = name.split(".")[-1]
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{short}")
