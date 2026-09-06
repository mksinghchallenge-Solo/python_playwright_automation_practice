"""
Response validator - fluent assertions for :class:`ApiResponse`.

Every failure message includes the full masked request + response so you
immediately see *what* was sent and *what* came back.

Example::

    (ResponseValidator(response)
        .status(200)
        .content_type("application/json")
        .header_present("Content-Type")
        .response_time_below(1500)
        .field_equals("json.email", "user@example.com")
        .field_type("json.age", int)
        .field_not_null("json.id"))
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from api.models.api_response import ApiResponse
from utils.common.helpers import deep_get
from utils.logging.logger import get_logger

log = get_logger("ResponseValidator")

_MISSING = object()

# Security-relevant headers typically expected on public web APIs.
SECURITY_HEADERS: tuple[str, ...] = (
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Content-Security-Policy",
)


class ApiAssertionError(AssertionError):
    """AssertionError carrying the request/response report."""

    def __init__(self, message: str, response: ApiResponse) -> None:
        super().__init__(f"{message}\n--- {response.describe()} ---\n{response.failure_report()}")


class ResponseValidator:
    """Chainable validations for an API response."""

    def __init__(self, response: ApiResponse) -> None:
        self.response = response

    def _fail(self, message: str) -> None:
        log.error("VALIDATION FAILED | %s | %s", self.response.describe(), message)
        raise ApiAssertionError(message, self.response)

    # -------------------------------------------------------- status code
    def status(self, expected: int) -> ResponseValidator:
        if self.response.status_code != expected:
            self._fail(f"Expected status {expected} but got {self.response.status_code}")
        return self

    def status_in(self, expected: Iterable[int]) -> ResponseValidator:
        allowed = list(expected)
        if self.response.status_code not in allowed:
            self._fail(f"Expected status in {allowed} but got {self.response.status_code}")
        return self

    def success(self) -> ResponseValidator:
        return self.status_in(range(200, 300))

    def client_error(self) -> ResponseValidator:
        return self.status_in(range(400, 500))

    # ------------------------------------------------------------ headers
    def header_present(self, name: str) -> ResponseValidator:
        if self.response.header(name) is None:
            self._fail(f"Expected response header '{name}' to be present")
        return self

    def header_equals(self, name: str, expected: str) -> ResponseValidator:
        actual = self.response.header(name)
        if actual != expected:
            self._fail(f"Header '{name}' expected '{expected}' but got '{actual}'")
        return self

    def header_contains(self, name: str, fragment: str) -> ResponseValidator:
        actual = self.response.header(name) or ""
        if fragment.lower() not in actual.lower():
            self._fail(f"Header '{name}'='{actual}' does not contain '{fragment}'")
        return self

    def content_type(self, expected: str = "application/json") -> ResponseValidator:
        return self.header_contains("Content-Type", expected)

    def correlation_id_present(
        self, candidates: Iterable[str] = ("X-Request-Id", "X-Correlation-Id", "Request-Id")
    ) -> ResponseValidator:
        if not any(self.response.header(name) for name in candidates):
            self._fail(f"No correlation/request id header found (looked for {list(candidates)})")
        return self

    def cache_control_present(self) -> ResponseValidator:
        return self.header_present("Cache-Control")

    def security_headers_present(
        self, headers: Iterable[str] = SECURITY_HEADERS, strict: bool = False
    ) -> ResponseValidator:
        missing = [h for h in headers if self.response.header(h) is None]
        if missing:
            message = f"Missing security headers: {missing}"
            if strict:
                self._fail(message)
            log.warning("%s | %s", self.response.describe(), message)
        return self

    # ------------------------------------------------------------ timing
    def response_time_below(self, max_ms: float) -> ResponseValidator:
        if self.response.elapsed_ms > max_ms:
            self._fail(f"Response time {self.response.elapsed_ms} ms exceeded threshold {max_ms} ms")
        return self

    # --------------------------------------------------------------- body
    def is_json(self) -> ResponseValidator:
        try:
            self.response.json()
        except ValueError as exc:
            self._fail(str(exc))
        return self

    def _value(self, path: str) -> Any:
        return deep_get(self.response.json(), path, _MISSING)

    def field_present(self, path: str) -> ResponseValidator:
        if self._value(path) is _MISSING:
            self._fail(f"Field '{path}' missing from response body")
        return self

    def fields_present(self, paths: Iterable[str]) -> ResponseValidator:
        missing = [p for p in paths if self._value(p) is _MISSING]
        if missing:
            self._fail(f"Fields missing from response body: {missing}")
        return self

    def field_absent(self, path: str) -> ResponseValidator:
        if self._value(path) is not _MISSING:
            self._fail(f"Field '{path}' should NOT be present in response body")
        return self

    def field_equals(self, path: str, expected: Any) -> ResponseValidator:
        actual = self._value(path)
        if actual is _MISSING:
            self._fail(f"Field '{path}' missing (expected {expected!r})")
        if actual != expected:
            self._fail(f"Field '{path}' expected {expected!r} but got {actual!r}")
        return self

    def field_contains(self, path: str, fragment: str) -> ResponseValidator:
        actual = self._value(path)
        if actual is _MISSING or fragment not in str(actual):
            self._fail(f"Field '{path}'={actual!r} does not contain {fragment!r}")
        return self

    def field_type(self, path: str, expected_type: type | tuple[type, ...]) -> ResponseValidator:
        actual = self._value(path)
        if actual is _MISSING:
            self._fail(f"Field '{path}' missing (expected type {expected_type})")
        if not isinstance(actual, expected_type):
            self._fail(f"Field '{path}' expected type {expected_type} but got {type(actual).__name__}: {actual!r}")
        return self

    def field_not_null(self, path: str) -> ResponseValidator:
        actual = self._value(path)
        if actual is _MISSING or actual is None:
            self._fail(f"Field '{path}' is null or missing")
        return self

    def field_is_null(self, path: str) -> ResponseValidator:
        actual = self._value(path)
        if actual is not None:
            self._fail(f"Field '{path}' expected null but got {actual!r}")
        return self

    def field_matches(self, path: str, predicate: Any, description: str = "custom predicate") -> ResponseValidator:
        actual = self._value(path)
        if actual is _MISSING or not predicate(actual):
            self._fail(f"Field '{path}'={actual!r} failed check: {description}")
        return self

    def list_not_empty(self, path: str) -> ResponseValidator:
        actual = self._value(path)
        if not isinstance(actual, list) or not actual:
            self._fail(f"Field '{path}' expected a non-empty list but got {actual!r}")
        return self

    def body_contains(self, fragment: str) -> ResponseValidator:
        if fragment not in self.response.text:
            self._fail(f"Response body does not contain {fragment!r}")
        return self
