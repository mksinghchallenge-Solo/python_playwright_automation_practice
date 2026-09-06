"""
Base API client.

Every concrete client (AuthClient, ProfileClient...) inherits from
:class:`BaseAPIClient`. The base client centralises:

* HTTP verbs: GET / POST / PUT / PATCH / DELETE / HEAD / OPTIONS
* headers, query params, path params, JSON, form, multipart, cookies
* authentication (Bearer token / API key / custom header) via an AuthProvider
* timeouts, SSL verification, proxies
* controlled retries for transient network errors / 5xx / 429
* structured request/response logging with secret masking
* request/response artifacts + Allure attachments
* response-time measurement

Concrete clients only describe *endpoints*; they never repeat plumbing.

IMPORTANT: this module must never import Playwright.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any, Protocol

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from api.models.api_response import ApiRequestRecord, ApiResponse
from utils.artifacts.artifact_manager import get_artifact_manager, safe_name
from utils.common.helpers import join_url
from utils.config.config_reader import get_config
from utils.logging.logger import get_logger
from utils.logging.masking import mask_data, mask_headers, mask_url
from utils.reporting.allure_manager import api_call_step, attach_json


class AuthProvider(Protocol):
    """Anything that can add authentication headers to a request."""

    def auth_headers(self) -> dict[str, str]: ...


class ApiClientError(Exception):
    """Raised when an HTTP request could not be completed at all."""


class BaseAPIClient:
    """Reusable HTTP client built on ``requests``."""

    DEFAULT_HEADERS: dict[str, str] = {
        "Accept": "application/json",
        "User-Agent": "coca-cola-automation/1.0 (+pytest)",
    }

    def __init__(
        self,
        base_url: str,
        *,
        name: str | None = None,
        auth_provider: AuthProvider | None = None,
        timeout: float | None = None,
        verify_ssl: bool = True,
        proxies: Mapping[str, str] | None = None,
        default_headers: Mapping[str, str] | None = None,
        max_retries: int = 2,
        save_artifacts: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.name = name or self.__class__.__name__
        self.auth_provider = auth_provider
        self.timeout = timeout or get_config().api_timeout_seconds
        self.verify_ssl = verify_ssl
        self.proxies = dict(proxies) if proxies else None
        self.save_artifacts = save_artifacts
        self.log = get_logger(self.name)
        self.session = self._build_session(max_retries)
        self.session.headers.update(self.DEFAULT_HEADERS)
        if default_headers:
            self.session.headers.update(default_headers)
        self.last_response: ApiResponse | None = None

    # ------------------------------------------------------------ session
    @staticmethod
    def _build_session(max_retries: int) -> requests.Session:
        """Session with conservative retries for transient failures only."""
        session = requests.Session()
        retry = Retry(
            total=max_retries,
            connect=max_retries,
            read=max_retries,
            backoff_factor=0.5,
            status_forcelist=(429, 502, 503, 504),
            allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),  # never retry writes blindly
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def set_header(self, name: str, value: str) -> None:
        self.session.headers[name] = value

    def set_cookie(self, name: str, value: str, domain: str | None = None) -> None:
        self.session.cookies.set(name, value, domain=domain)

    def close(self) -> None:
        self.session.close()

    # ---------------------------------------------------------------- url
    def build_url(self, path: str, path_params: Mapping[str, Any] | None = None) -> str:
        """Join base URL + path and substitute ``{placeholders}``."""
        if path_params:
            path = path.format(**path_params)
        return join_url(self.base_url, path)

    # -------------------------------------------------------------- verbs
    def get(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("DELETE", path, **kwargs)

    def head(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("HEAD", path, **kwargs)

    def options(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("OPTIONS", path, **kwargs)

    # ------------------------------------------------------------ request
    def request(
        self,
        method: str,
        path: str,
        *,
        path_params: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        cookies: Mapping[str, str] | None = None,
        timeout: float | None = None,
        authenticate: bool = True,
        allow_redirects: bool = True,
        artifact_name: str | None = None,
    ) -> ApiResponse:
        """Send an HTTP request and return an :class:`ApiResponse`.

        Never raises for HTTP error statuses - tests assert on them explicitly.
        Raises :class:`ApiClientError` only for transport failures.
        """
        method = method.upper()
        url = self.build_url(path, path_params)
        merged_headers: dict[str, str] = dict(self.session.headers)
        if authenticate and self.auth_provider is not None:
            merged_headers.update(self.auth_provider.auth_headers())
        if headers:
            merged_headers.update(headers)

        record = ApiRequestRecord(
            method=method,
            url=url,
            headers=merged_headers,
            params=dict(params) if params else None,
            json_body=json,
            data=data,
            files=files,
            cookies=dict(cookies) if cookies else None,
        )
        self._log_request(record)

        started = time.perf_counter()
        with api_call_step(method, url):
            try:
                raw = self.session.request(
                    method,
                    url,
                    params=params,
                    headers=merged_headers,
                    json=json,
                    data=data,
                    files=files,
                    cookies=dict(cookies) if cookies else None,
                    timeout=timeout or self.timeout,
                    verify=self.verify_ssl,
                    proxies=self.proxies,
                    allow_redirects=allow_redirects,
                )
            except requests.RequestException as exc:
                elapsed = (time.perf_counter() - started) * 1000
                self.log.error(
                    "API TRANSPORT ERROR | %s %s | %.0f ms | %s: %s",
                    method,
                    mask_url(url),
                    elapsed,
                    exc.__class__.__name__,
                    exc,
                )
                attach_json(f"{method} {mask_url(url)} - request", record.to_dict())
                raise ApiClientError(
                    f"{method} {mask_url(url)} failed after {elapsed:.0f} ms: " f"{exc.__class__.__name__}: {exc}"
                ) from exc

            elapsed = (time.perf_counter() - started) * 1000
            response = ApiResponse(raw, record, elapsed)
            self.last_response = response
            self._log_response(response)
            self._persist(artifact_name or f"{method}_{safe_name(path)}", record, response)
        return response

    # ------------------------------------------------------------ logging
    def _log_request(self, record: ApiRequestRecord) -> None:
        self.log.info("API REQUEST  | %s %s", record.method, mask_url(record.url))
        if record.params:
            self.log.debug("  params : %s", mask_data(record.params))
        self.log.debug("  headers: %s", mask_headers(record.headers))
        if record.json_body is not None:
            self.log.debug("  json   : %s", mask_data(record.json_body))
        elif record.data is not None:
            self.log.debug("  data   : %s", mask_data(record.data))

    def _log_response(self, response: ApiResponse) -> None:
        config = get_config()
        level = "info"
        if response.elapsed_ms > config.api_warn_ms:
            level = "warning"
        getattr(self.log, level)("API RESPONSE | %s | Response time: %.0f ms", response.describe(), response.elapsed_ms)
        if response.status_code >= 400:
            self.log.warning("API ERROR BODY | %s", response.to_dict(body_limit=2000)["body"])

    def _persist(self, name: str, record: ApiRequestRecord, response: ApiResponse) -> None:
        req_dict = record.to_dict()
        res_dict = response.to_dict()
        attach_json(f"{record.method} {mask_url(record.url)} - request", req_dict, mask=False)
        attach_json(f"{record.method} {mask_url(record.url)} - response", res_dict, mask=False)
        if self.save_artifacts:
            try:
                get_artifact_manager().save_api_exchange(name, req_dict, res_dict)
            except OSError as exc:  # artifact problems must never fail a test silently
                self.log.error("Could not persist API artifact for %s: %s", name, exc)
