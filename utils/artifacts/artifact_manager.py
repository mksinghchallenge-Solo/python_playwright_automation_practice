"""
Artifact manager.

Single place that decides *where* an artifact is written and *how* it is
named. Used by the Playwright fixtures (screenshots, videos, traces), the API
client (request/response dumps) and the reporting helpers.

Naming convention::

    <test_name>__<browser>__<device>__<worker>__<HH-MM-SS-ffffff>.<ext>

Example::

    test_login_success__chromium__Pixel-7__gw0__02-35-41-123456.png
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.logging.logger import get_logger
from utils.logging.masking import mask_data
from utils.reporting.execution_manager import ExecutionManager, get_execution_manager

log = get_logger("ArtifactManager")

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def safe_name(value: str, max_length: int = 80) -> str:
    """Convert any string into a filesystem-safe token."""
    cleaned = _SAFE_NAME.sub("-", value).strip("-")
    return cleaned[:max_length] or "unnamed"


class ArtifactManager:
    """Builds unique artifact paths and writes JSON/text artifacts."""

    def __init__(self, execution: ExecutionManager | None = None) -> None:
        self.execution = execution or get_execution_manager()

    # ------------------------------------------------------------- naming
    def build_name(
        self,
        test_name: str,
        extension: str,
        browser: str = "",
        device: str = "",
        suffix: str = "",
    ) -> str:
        parts = [safe_name(test_name)]
        if browser:
            parts.append(safe_name(browser))
        if device:
            parts.append(safe_name(device))
        if suffix:
            parts.append(safe_name(suffix))
        parts.append(self.execution.worker_id)
        parts.append(datetime.now().strftime("%H-%M-%S-%f"))
        return "__".join(parts) + "." + extension.lstrip(".")

    # -------------------------------------------------------------- paths
    def screenshot_path(self, test_name: str, browser: str, device: str, suffix: str = "") -> Path:
        return self.execution.path("ui", "screenshots", self.build_name(test_name, "png", browser, device, suffix))

    def video_path(self, test_name: str, browser: str, device: str) -> Path:
        return self.execution.path("ui", "videos", self.build_name(test_name, "webm", browser, device))

    def trace_path(self, test_name: str, browser: str, device: str) -> Path:
        return self.execution.path("ui", "traces", self.build_name(test_name, "zip", browser, device))

    def video_dir(self) -> Path:
        path = self.execution.execution_dir / "ui" / "videos" / f"raw_{self.execution.worker_id}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def api_request_path(self, name: str) -> Path:
        return self.execution.path("api", "requests", self.build_name(name, "json"))

    def api_response_path(self, name: str) -> Path:
        return self.execution.path("api", "responses", self.build_name(name, "json"))

    def e2e_path(self, name: str, extension: str = "json") -> Path:
        return self.execution.path("e2e", self.build_name(name, extension))

    def framework_path(self, name: str, extension: str = "json") -> Path:
        return self.execution.path("framework", self.build_name(name, extension))

    # ------------------------------------------------------------- writers
    def write_json(self, path: Path, data: Any, mask: bool = True) -> Path:
        """Write JSON with secrets masked (default) and return the path."""
        payload = mask_data(data) if mask else data
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        log.debug("Artifact written: %s", path)
        return path

    def write_text(self, path: Path, text: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        log.debug("Artifact written: %s", path)
        return path

    def save_api_exchange(self, name: str, request: dict[str, Any], response: dict[str, Any]) -> tuple[Path, Path]:
        """Persist a request + response pair (masked). Returns both paths."""
        request_path = self.write_json(self.api_request_path(name), request)
        response_path = self.write_json(self.api_response_path(name), response)
        return request_path, response_path


_artifact_singleton: ArtifactManager | None = None


def get_artifact_manager() -> ArtifactManager:
    global _artifact_singleton
    if _artifact_singleton is None:
        _artifact_singleton = ArtifactManager()
    return _artifact_singleton
