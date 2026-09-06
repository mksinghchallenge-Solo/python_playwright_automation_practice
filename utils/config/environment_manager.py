"""
Environment manager.

Resolves *which* environment (qa / staging / prod) is active and loads its
``config/environments/<env>.yaml`` file. Provides typed access to base URLs,
API endpoints and safety flags.

Example::

    from utils.config.environment_manager import get_environment
    env = get_environment()
    env.name            # "qa"
    env.ui_base_url     # "https://www.coca-cola.com/us/en"
    env.endpoint("profile")   # "<PROFILE_ENDPOINT>" until you replace it
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from utils.config.config_reader import CONFIG_DIR, get_config

ENVIRONMENTS_DIR = CONFIG_DIR / "environments"
SUPPORTED_ENVIRONMENTS = ("local", "qa", "staging", "prod")
PLACEHOLDER_PREFIX = "<"


class EnvironmentConfigError(Exception):
    """Raised when an environment file is missing or invalid."""


class Environment:
    """Typed view over one ``config/environments/<name>.yaml`` file."""

    def __init__(self, name: str) -> None:
        self.name = name.lower()
        if self.name not in SUPPORTED_ENVIRONMENTS:
            raise EnvironmentConfigError(
                f"Unknown environment '{name}'. Supported: {', '.join(SUPPORTED_ENVIRONMENTS)}"
            )
        self.file_path: Path = ENVIRONMENTS_DIR / f"{self.name}.yaml"
        self._data: dict[str, Any] = self._load()
        self._apply_env_overrides()

    def _load(self) -> dict[str, Any]:
        if not self.file_path.exists():
            raise EnvironmentConfigError(f"Environment file not found: {self.file_path}")
        with self.file_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise EnvironmentConfigError(f"Environment file must be a mapping: {self.file_path}")
        return data

    def _apply_env_overrides(self) -> None:
        """``UI_BASE_URL`` / ``API_BASE_URL`` env vars override the YAML file."""
        ui_url = os.getenv("UI_BASE_URL")
        api_url = os.getenv("API_BASE_URL")
        if ui_url:
            self._data.setdefault("ui", {})["base_url"] = ui_url
        if api_url:
            self._data.setdefault("api", {})["base_url"] = api_url

    # ------------------------------------------------------------ accessors
    def get(self, dotted_key: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    @property
    def ui_base_url(self) -> str:
        return str(self.get("ui.base_url", "")).rstrip("/")

    @property
    def api_base_url(self) -> str:
        return str(self.get("api.base_url", "")).rstrip("/")

    @property
    def example_api_base_url(self) -> str:
        """Safe public practice API used only to prove the API layer works."""
        return str(self.get("api.example_base_url", "https://httpbin.org")).rstrip("/")

    @property
    def verify_ssl(self) -> bool:
        return bool(self.get("api.verify_ssl", True))

    @property
    def api_timeout_seconds(self) -> int:
        return int(self.get("api.timeout_seconds", get_config().api_timeout_seconds))

    def endpoint(self, key: str) -> str:
        """Return the configured path for a logical endpoint name."""
        endpoints = self.get("api.endpoints", {}) or {}
        if key not in endpoints:
            raise EnvironmentConfigError(f"Endpoint '{key}' is not defined in {self.file_path} under api.endpoints")
        return str(endpoints[key])

    def is_placeholder(self, value: str) -> bool:
        """True when a URL/endpoint is still an unreplaced ``<PLACEHOLDER>``."""
        return value.strip().startswith(PLACEHOLDER_PREFIX)

    def api_is_configured(self) -> bool:
        """True only when the real API base URL has been provided."""
        return bool(self.api_base_url) and not self.is_placeholder(self.api_base_url)

    def endpoint_is_configured(self, key: str) -> bool:
        try:
            return self.api_is_configured() and not self.is_placeholder(self.endpoint(key))
        except EnvironmentConfigError:
            return False

    # --------------------------------------------------------------- safety
    @property
    def is_production(self) -> bool:
        return self.name == "prod"

    def allows(self, safety_level: str) -> bool:
        """Return whether the environment permits a test safety level."""
        flag = f"safety.allow_{safety_level.lower()}"
        return bool(self.get(flag, False))

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "file": str(self.file_path),
            "ui_base_url": self.ui_base_url,
            "api_base_url": self.api_base_url,
            "api_configured": self.api_is_configured(),
            "safety": self.get("safety", {}),
        }


_environment_singleton: Environment | None = None


def resolve_environment_name(cli_value: str | None = None) -> str:
    """CLI option > ENV variable > config.yaml default."""
    if cli_value:
        return cli_value.lower()
    return (os.getenv("ENV") or get_config().environment).lower()


def get_environment(name: str | None = None, reload: bool = False) -> Environment:
    """Return the active :class:`Environment` (cached)."""
    global _environment_singleton
    if _environment_singleton is None or reload or (name and _environment_singleton.name != name.lower()):
        _environment_singleton = Environment(resolve_environment_name(name))
    return _environment_singleton
