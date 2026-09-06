"""
Allure helper functions.

Thin wrappers around ``allure`` so tests and fixtures do not need to know the
Allure API. Everything is safe to call when Allure is not installed (calls
become no-ops), which keeps the framework usable without the plugin.

Typical usage inside a test::

    from utils.reporting.allure_manager import step, attach_json, attach_text

    with step("Login with valid user"):
        login_page.login(user)
    attach_json("profile", profile_response.json())
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from pathlib import Path
from typing import Any

from utils.logging.masking import mask_data, mask_text

try:  # pragma: no cover - import guard
    import allure
    from allure_commons.types import AttachmentType

    ALLURE_AVAILABLE = True
except ImportError:  # pragma: no cover
    allure = None  # type: ignore[assignment]
    AttachmentType = None  # type: ignore[assignment,misc]
    ALLURE_AVAILABLE = False


def step(title: str) -> AbstractContextManager[Any]:
    """Allure step context manager (no-op without Allure)."""
    if ALLURE_AVAILABLE:
        return allure.step(title)
    return nullcontext()


def attach_text(name: str, text: str, mask: bool = True) -> None:
    if not ALLURE_AVAILABLE:
        return
    allure.attach(mask_text(text) if mask else text, name=name, attachment_type=AttachmentType.TEXT)


def attach_json(name: str, data: Any, mask: bool = True) -> None:
    if not ALLURE_AVAILABLE:
        return
    payload = mask_data(data) if mask else data
    allure.attach(
        json.dumps(payload, indent=2, default=str),
        name=name,
        attachment_type=AttachmentType.JSON,
    )


def attach_file(path: Path, name: str | None = None) -> None:
    """Attach a file, choosing the attachment type from its extension."""
    if not ALLURE_AVAILABLE or not path.exists():
        return
    mapping = {
        ".png": AttachmentType.PNG,
        ".jpg": AttachmentType.JPG,
        ".webm": AttachmentType.WEBM,
        ".mp4": AttachmentType.MP4,
        ".html": AttachmentType.HTML,
        ".json": AttachmentType.JSON,
        ".txt": AttachmentType.TEXT,
        ".log": AttachmentType.TEXT,
        ".zip": None,  # traces - attached as generic file
    }
    attachment_type = mapping.get(path.suffix.lower(), AttachmentType.TEXT)
    if attachment_type is None:
        allure.attach.file(str(path), name=name or path.name, extension=path.suffix.lstrip("."))
    else:
        allure.attach.file(str(path), name=name or path.name, attachment_type=attachment_type)


def add_labels(**labels: str) -> None:
    """Add dynamic labels, e.g. ``add_labels(browser="chromium", device="Pixel 7")``."""
    if not ALLURE_AVAILABLE:
        return
    for key, value in labels.items():
        if value:
            allure.dynamic.label(key, str(value))


def add_parameter(name: str, value: Any) -> None:
    if ALLURE_AVAILABLE:
        allure.dynamic.parameter(name, mask_data(value))


def add_link(url: str, name: str | None = None) -> None:
    if ALLURE_AVAILABLE:
        allure.dynamic.link(url, name=name or url)


def write_environment_properties(results_dir: Path, properties: dict[str, Any]) -> Path:
    """Create ``environment.properties`` shown on the Allure overview page."""
    results_dir.mkdir(parents=True, exist_ok=True)
    target = results_dir / "environment.properties"
    lines = [f"{key}={mask_text(str(value))}" for key, value in properties.items()]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def write_executor_json(results_dir: Path, execution_id: str, build_url: str = "") -> Path:
    """Create ``executor.json`` so Allure shows where the run came from."""
    results_dir.mkdir(parents=True, exist_ok=True)
    target = results_dir / "executor.json"
    payload = {
        "name": "Coca-Cola Automation",
        "type": "pytest",
        "buildName": execution_id,
        "buildUrl": build_url,
        "reportName": f"Execution {execution_id}",
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


@contextmanager
def api_call_step(method: str, url: str) -> Iterator[None]:
    """Convenience step used by the API client for readable Allure trees."""
    with step(f"{method.upper()} {mask_text(url)}"):
        yield
