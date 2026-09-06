"""
Central configuration reader.

Loads ``config/config.yaml`` once, applies environment-variable overrides and
exposes simple, typed accessors. Nothing else in the framework should read
YAML config files directly - always go through :class:`ConfigReader`.

Example::

    from utils.config.config_reader import get_config
    config = get_config()
    config.browser_name        # "chromium"
    config.get("timeouts.page_load_ms")   # 45000
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
MAIN_CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Load .env once, without overriding variables already present in the shell
# (so CI variables always win over the local .env file).
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _as_bool(value: str | bool | None, default: bool) -> bool:
    """Convert common string representations to a boolean."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


class ConfigReader:
    """Reads the main YAML configuration and applies environment overrides."""

    def __init__(self, config_file: Path = MAIN_CONFIG_FILE) -> None:
        self.config_file = config_file
        self._data: dict[str, Any] = self._load_yaml(config_file)
        self._apply_env_overrides()

    # ------------------------------------------------------------------ load
    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Configuration root must be a mapping: {path}")
        return data

    def _apply_env_overrides(self) -> None:
        """Environment variables override YAML defaults (12-factor style)."""
        env_map: dict[str, tuple[str, type]] = {
            "ENV": ("environment", str),
            "BROWSER": ("browser.name", str),
            "HEADLESS": ("browser.headless", bool),
            "SLOW_MO": ("browser.slow_mo", int),
            "MOBILE_DEVICE": ("mobile.device", str),
            "MOBILE_ENABLED": ("mobile.enabled", bool),
            "SCREENSHOT_MODE": ("artifacts.screenshots", str),
            "VIDEO_MODE": ("artifacts.videos", str),
            "TRACE_MODE": ("artifacts.traces", str),
            "RETRIES": ("execution.retries", int),
            "MASK_SECRETS": ("security.mask_secrets", bool),
            "API_TIMEOUT_SECONDS": ("timeouts.api_seconds", int),
            "RETENTION_DAYS": ("retention.days", int),
            "RETENTION_EXECUTIONS": ("retention.executions", int),
            "RETENTION_ENABLED": ("retention.enabled", bool),
        }
        for env_name, (dotted_key, cast) in env_map.items():
            raw = os.getenv(env_name)
            if raw is None or raw == "":
                continue
            if cast is bool:
                value: Any = _as_bool(raw, False)
            elif cast is int:
                value = int(raw)
            else:
                value = raw
            self.set(dotted_key, value)

    # --------------------------------------------------------------- access
    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Return a nested value using dotted notation, e.g. ``browser.name``."""
        node: Any = self._data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted_key: str, value: Any) -> None:
        """Set a nested value (used for CLI/env overrides)."""
        parts = dotted_key.split(".")
        node = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def as_dict(self) -> dict[str, Any]:
        """Return a copy of the full configuration."""
        return dict(self._data)

    # ---------------------------------------------------- typed convenience
    @property
    def environment(self) -> str:
        return str(self.get("environment", "qa")).lower()

    @property
    def browser_name(self) -> str:
        return str(self.get("browser.name", "chromium")).lower()

    @property
    def headless(self) -> bool:
        return _as_bool(self.get("browser.headless", True), True)

    @property
    def slow_mo(self) -> int:
        return int(self.get("browser.slow_mo", 0))

    @property
    def viewport(self) -> dict[str, int]:
        vp = self.get("browser.viewport", {}) or {}
        return {"width": int(vp.get("width", 1920)), "height": int(vp.get("height", 1080))}

    @property
    def mobile_enabled(self) -> bool:
        return _as_bool(self.get("mobile.enabled", False), False)

    @property
    def mobile_device(self) -> str:
        return str(self.get("mobile.device", "Pixel 7"))

    @property
    def screenshot_mode(self) -> str:
        return str(self.get("artifacts.screenshots", "retain-on-failure"))

    @property
    def video_mode(self) -> str:
        return str(self.get("artifacts.videos", "retain-on-failure"))

    @property
    def trace_mode(self) -> str:
        return str(self.get("artifacts.traces", "retain-on-failure"))

    @property
    def mask_secrets(self) -> bool:
        return _as_bool(self.get("security.mask_secrets", True), True)

    @property
    def page_load_timeout_ms(self) -> int:
        return int(self.get("timeouts.page_load_ms", 45000))

    @property
    def action_timeout_ms(self) -> int:
        return int(self.get("timeouts.action_ms", 15000))

    @property
    def expect_timeout_ms(self) -> int:
        return int(self.get("timeouts.expect_ms", 15000))

    @property
    def api_timeout_seconds(self) -> int:
        return int(self.get("timeouts.api_seconds", 30))

    @property
    def api_warn_ms(self) -> int:
        return int(self.get("performance.api_response_time_warn_ms", 1500))

    @property
    def api_fail_ms(self) -> int:
        return int(self.get("performance.api_response_time_fail_ms", 10000))


_config_singleton: ConfigReader | None = None


def get_config(reload: bool = False) -> ConfigReader:
    """Return the shared :class:`ConfigReader` (created on first use)."""
    global _config_singleton
    if _config_singleton is None or reload:
        _config_singleton = ConfigReader()
    return _config_singleton
