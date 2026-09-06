"""
Playwright ``page.route()`` helpers for *UI-layer* mocking.

Use these when a UI test needs a backend call to return deterministic data
(or to fail) without depending on the real service. This module lives in
``api/mocks`` because it describes API *payloads*; it is invoked from UI
tests/fixtures which own the ``page`` object.

Example::

    from api.mocks.ui_route_mocks import mock_json_response
    mock_json_response(page, "**/api/v1/users/me", {"first_name": "Mocked"})
    page.goto("/profile")
"""

from __future__ import annotations

import json
from typing import Any

from playwright.sync_api import Page, Route

from utils.logging.logger import get_logger

log = get_logger("UiRouteMocks")


def mock_json_response(
    page: Page, url_pattern: str, body: Any, status: int = 200, headers: dict[str, str] | None = None
) -> None:
    """Fulfil every request matching ``url_pattern`` with a JSON body."""

    def _fulfil(route: Route) -> None:
        log.info("UI MOCK | %s %s -> %s", route.request.method, route.request.url, status)
        route.fulfill(status=status, content_type="application/json", headers=headers or {}, body=json.dumps(body))

    page.route(url_pattern, _fulfil)


def mock_failure(page: Page, url_pattern: str, status: int = 500, message: str = "mocked failure") -> None:
    mock_json_response(page, url_pattern, {"error": message}, status=status)


def block_requests(page: Page, url_pattern: str) -> None:
    """Abort matching requests (e.g. third-party analytics) to speed up tests."""

    def _abort(route: Route) -> None:
        log.debug("UI BLOCK | %s", route.request.url)
        route.abort()

    page.route(url_pattern, _abort)


def block_common_third_parties(page: Page) -> None:
    """Block typical trackers/ads that slow UI tests and add flakiness."""
    for pattern in (
        "**/*doubleclick*/**",
        "**/*googletagmanager*/**",
        "**/*google-analytics*/**",
        "**/*facebook.net/**",
        "**/*hotjar*/**",
    ):
        block_requests(page, pattern)
