"""
Profile client - read and update the logged-in user's profile.

Endpoints are placeholders (``<PROFILE_ENDPOINT>``, ``<UPDATE_PROFILE_ENDPOINT>``)
until replaced in ``config/environments/<env>.yaml``.
"""

from __future__ import annotations

from typing import Any

from api.clients.base_client import AuthProvider, BaseAPIClient
from api.models.api_response import ApiResponse
from utils.config.environment_manager import Environment, get_environment


class ProfileClient(BaseAPIClient):
    """Profile endpoints - requires an ``auth_provider`` (TokenManager)."""

    def __init__(
        self, environment: Environment | None = None, auth_provider: AuthProvider | None = None, **kwargs: Any
    ) -> None:
        self.environment = environment or get_environment()
        super().__init__(
            self.environment.api_base_url,
            name="ProfileClient",
            auth_provider=auth_provider,
            verify_ssl=self.environment.verify_ssl,
            timeout=self.environment.api_timeout_seconds,
            **kwargs,
        )

    def get_profile(self) -> ApiResponse:
        """GET <PROFILE_ENDPOINT> (READ_ONLY)."""
        return self.get(self.environment.endpoint("profile"), artifact_name="profile_get")

    def update_profile(self, payload: dict[str, Any]) -> ApiResponse:
        """PUT <UPDATE_PROFILE_ENDPOINT> (DATA_MODIFYING)."""
        return self.put(self.environment.endpoint("update_profile"), json=payload, artifact_name="profile_update")

    def patch_profile(self, payload: dict[str, Any]) -> ApiResponse:
        """PATCH <UPDATE_PROFILE_ENDPOINT> (DATA_MODIFYING)."""
        return self.patch(self.environment.endpoint("update_profile"), json=payload, artifact_name="profile_patch")
