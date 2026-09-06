"""
Runtime context.

A tiny, explicit data holder describing *how* the current run is configured
(environment, browser, device, headless...). It is built once per process in
``conftest.py`` from CLI options + config and shared with fixtures, page
objects and reporting - so nobody has to re-parse pytest options.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RuntimeContext:
    """Immutable-ish description of the active run."""

    environment: str = "qa"
    browser: str = "chromium"
    channel: str | None = None  # "chrome" / "msedge" for branded Chromium
    headless: bool = True
    slow_mo: int = 0
    device: str | None = None  # None == desktop
    device_descriptor: dict[str, Any] = field(default_factory=dict)
    screenshot_mode: str = "retain-on-failure"
    video_mode: str = "retain-on-failure"
    trace_mode: str = "retain-on-failure"
    ui_base_url: str = ""
    api_base_url: str = ""
    worker_id: str = "main"
    execution_id: str = ""
    execution_dir: str = ""

    @property
    def is_mobile(self) -> bool:
        return bool(self.device)

    @property
    def device_label(self) -> str:
        return self.device or "desktop"

    @property
    def browser_label(self) -> str:
        return self.channel or self.browser

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["is_mobile"] = self.is_mobile
        return data
