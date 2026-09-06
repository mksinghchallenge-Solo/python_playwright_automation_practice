"""
Framework-level API response wrapper.

Wraps a ``requests.Response`` and adds what tests actually need: timing,
convenient JSON access and a masked, serialisable representation used for
logging, artifacts and Allure attachments.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import requests

from utils.logging.masking import mask_data, mask_headers, mask_url


@dataclass
class ApiRequestRecord:
    """Everything sent to the server (masked when serialised)."""

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] | None = None
    json_body: Any = None
    data: Any = None
    files: Any = None
    cookies: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "url": mask_url(self.url),
            "headers": mask_headers(self.headers),
            "params": mask_data(self.params),
            "json": mask_data(self.json_body),
            "data": mask_data(self.data),
            "files": list(self.files.keys()) if isinstance(self.files, dict) else None,
            "cookies": mask_data(self.cookies),
        }


class ApiResponse:
    """Wrapper around ``requests.Response`` with timing and helpers."""

    def __init__(self, raw: requests.Response, request_record: ApiRequestRecord, elapsed_ms: float) -> None:
        self.raw = raw
        self.request_record = request_record
        self.elapsed_ms = round(elapsed_ms, 2)

    # ------------------------------------------------------------- basics
    @property
    def status_code(self) -> int:
        return self.raw.status_code

    @property
    def ok(self) -> bool:
        return self.raw.ok

    @property
    def headers(self) -> dict[str, str]:
        return dict(self.raw.headers)

    @property
    def text(self) -> str:
        return self.raw.text

    @property
    def url(self) -> str:
        return self.raw.url

    @property
    def content_type(self) -> str:
        return self.raw.headers.get("Content-Type", "")

    @property
    def is_json(self) -> bool:
        return "json" in self.content_type.lower()

    def json(self) -> Any:
        """Parsed JSON body; raises a readable error when not JSON."""
        try:
            return self.raw.json()
        except (ValueError, json.JSONDecodeError) as exc:
            snippet = self.raw.text[:300]
            raise ValueError(
                f"Response from {self.request_record.method} {mask_url(self.url)} is not valid JSON "
                f"(status={self.status_code}, content-type='{self.content_type}'). Body starts with: {snippet!r}"
            ) from exc

    def json_or_none(self) -> Any:
        try:
            return self.raw.json()
        except ValueError:
            return None

    def header(self, name: str, default: str | None = None) -> str | None:
        return self.raw.headers.get(name, default)

    # ------------------------------------------------------- serialisation
    def to_dict(self, body_limit: int = 20000) -> dict[str, Any]:
        body: Any = self.json_or_none()
        if body is None:
            body = self.raw.text[:body_limit]
        return {
            "status_code": self.status_code,
            "reason": self.raw.reason,
            "url": mask_url(self.url),
            "elapsed_ms": self.elapsed_ms,
            "headers": mask_headers(self.headers),
            "body": mask_data(body),
        }

    def describe(self) -> str:
        """One-line human description used in assertion messages."""
        return f"{self.request_record.method} {mask_url(self.url)} -> {self.status_code} " f"({self.elapsed_ms} ms)"

    def failure_report(self) -> str:
        """Multi-line report attached to assertion errors."""
        return json.dumps(
            {"request": self.request_record.to_dict(), "response": self.to_dict(body_limit=5000)},
            indent=2,
            default=str,
        )
