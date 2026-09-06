"""
Authentication client + token manager.

Two responsibilities, kept separate:

* :class:`AuthClient` - talks to the (placeholder) auth endpoints.
* :class:`TokenManager` - caches tokens, tracks expiry, refreshes on demand
  and implements the ``AuthProvider`` protocol used by every other client.

REAL ENDPOINTS ARE NOT KNOWN. The paths come from
``config/environments/<env>.yaml -> api.endpoints`` where they are
``<AUTH_ENDPOINT>``-style placeholders. Replace them once you have discovered
and are authorized to use the real API (see docs/api_discovery.md).

The *shape* of the login response is also an assumption. Adjust
:meth:`TokenManager._parse_token_response` to the real payload.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any

from api.clients.base_client import BaseAPIClient
from api.models.api_response import ApiResponse
from utils.config.environment_manager import Environment, get_environment
from utils.logging.logger import get_logger

log = get_logger("TokenManager")


@dataclass
class Token:
    """An access token with expiry bookkeeping."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_at: float = 0.0  # epoch seconds; 0 == unknown/never

    def is_expired(self, leeway_seconds: int = 30) -> bool:
        if not self.expires_at:
            return False
        return time.time() >= (self.expires_at - leeway_seconds)


class AuthClient(BaseAPIClient):
    """Endpoints related to authentication (login / refresh / logout)."""

    def __init__(self, environment: Environment | None = None, **kwargs: Any) -> None:
        self.environment = environment or get_environment()
        super().__init__(
            self.environment.api_base_url,
            name="AuthClient",
            verify_ssl=self.environment.verify_ssl,
            timeout=self.environment.api_timeout_seconds,
            **kwargs,
        )

    def login(self, email: str, password: str, **extra_fields: Any) -> ApiResponse:
        """POST <AUTH_ENDPOINT> with credentials. Never logs the password."""
        payload = {"email": email, "password": password, **extra_fields}
        return self.post(
            self.environment.endpoint("login"), json=payload, authenticate=False, artifact_name="auth_login"
        )

    def login_raw(self, payload: Any, headers: dict[str, str] | None = None) -> ApiResponse:
        """Send an arbitrary body - used by negative/malformed-payload tests."""
        if isinstance(payload, (dict, list)):
            return self.post(
                self.environment.endpoint("login"),
                json=payload,
                authenticate=False,
                headers=headers,
                artifact_name="auth_login_raw",
            )
        return self.post(
            self.environment.endpoint("login"),
            data=payload,
            authenticate=False,
            headers={"Content-Type": "application/json", **(headers or {})},
            artifact_name="auth_login_raw",
        )

    def refresh(self, refresh_token: str) -> ApiResponse:
        return self.post(
            self.environment.endpoint("refresh"),
            json={"refresh_token": refresh_token},
            authenticate=False,
            artifact_name="auth_refresh",
        )

    def logout(self, token: str) -> ApiResponse:
        return self.post(
            self.environment.endpoint("logout"),
            headers={"Authorization": f"Bearer {token}"},
            authenticate=False,
            artifact_name="auth_logout",
        )

    def signup(self, user_payload: dict[str, Any]) -> ApiResponse:
        return self.post(
            self.environment.endpoint("signup"), json=user_payload, authenticate=False, artifact_name="auth_signup"
        )


class TokenManager:
    """Caches and refreshes tokens; acts as ``AuthProvider`` for other clients.

    Thread-safe so parallel workers / threads sharing an instance are fine.
    A static token can also be injected via ``API_STATIC_TOKEN`` (from .env)
    for environments where a long-lived test token is provided.
    """

    def __init__(self, auth_client: AuthClient, email: str | None = None, password: str | None = None) -> None:
        self.auth_client = auth_client
        self.email = email or os.getenv("API_USER_EMAIL", "")
        self.password = password or os.getenv("API_USER_PASSWORD", "")
        self._token: Token | None = None
        self._lock = threading.Lock()
        static = os.getenv("API_STATIC_TOKEN")
        if static:
            self._token = Token(access_token=static)
            log.info("Using static API token from environment (value masked)")

    # ------------------------------------------------------ AuthProvider
    def auth_headers(self) -> dict[str, str]:
        token = self.get_token()
        return {"Authorization": f"{token.token_type} {token.access_token}"}

    # ------------------------------------------------------------ tokens
    def get_token(self, force_refresh: bool = False) -> Token:
        with self._lock:
            if self._token is None or force_refresh:
                self._token = self._login()
            elif self._token.is_expired():
                self._token = self._refresh_or_login()
            return self._token

    def invalidate(self) -> None:
        with self._lock:
            self._token = None

    def _login(self) -> Token:
        if not self.email or not self.password:
            raise RuntimeError(
                "API credentials missing. Set API_USER_EMAIL and API_USER_PASSWORD in .env "
                "(see .env.example). Never hardcode them."
            )
        response = self.auth_client.login(self.email, self.password)
        if response.status_code not in (200, 201):
            raise RuntimeError(f"Login failed: {response.describe()}\n{response.failure_report()}")
        token = self._parse_token_response(response.json())
        log.info("Obtained new access token (masked); expires_at=%s", token.expires_at or "unknown")
        return token

    def _refresh_or_login(self) -> Token:
        if self._token and self._token.refresh_token:
            response = self.auth_client.refresh(self._token.refresh_token)
            if response.status_code == 200:
                log.info("Access token refreshed")
                return self._parse_token_response(response.json())
            log.warning("Refresh failed (%s); falling back to login", response.status_code)
        return self._login()

    @staticmethod
    def _parse_token_response(body: dict[str, Any]) -> Token:
        """Map the auth response to :class:`Token`.

        ASSUMED SHAPE (adjust to the real API)::

            {"access_token": "...", "refresh_token": "...", "token_type": "Bearer", "expires_in": 3600}
        """
        access = body.get("access_token") or body.get("token") or body.get("accessToken")
        if not access:
            raise RuntimeError(f"Could not find an access token in login response keys: {list(body)}")
        expires_in = body.get("expires_in") or body.get("expiresIn")
        expires_at = time.time() + float(expires_in) if expires_in else 0.0
        return Token(
            access_token=str(access),
            refresh_token=body.get("refresh_token") or body.get("refreshToken"),
            token_type=str(body.get("token_type") or body.get("tokenType") or "Bearer"),
            expires_at=expires_at,
        )


class StaticTokenProvider:
    """Simplest ``AuthProvider`` - useful for tests with a known/invalid token."""

    def __init__(self, token: str, token_type: str = "Bearer") -> None:
        self.token = token
        self.token_type = token_type

    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"{self.token_type} {self.token}"}


class ApiKeyProvider:
    """``AuthProvider`` for APIs that use an API-key header."""

    def __init__(self, api_key: str, header_name: str = "X-API-Key") -> None:
        self.api_key = api_key
        self.header_name = header_name

    def auth_headers(self) -> dict[str, str]:
        return {self.header_name: self.api_key}
