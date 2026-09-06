"""
User client - account lifecycle endpoints (create / fetch / delete user).

All paths are placeholders from ``config/environments/<env>.yaml`` until you
replace them with authorized endpoints. See docs/api_discovery.md.
"""

from __future__ import annotations

from typing import Any

from api.clients.base_client import AuthProvider, BaseAPIClient
from api.models.api_response import ApiResponse
from utils.config.environment_manager import Environment, get_environment


class UserClient(BaseAPIClient):
    """Endpoints that manage user accounts."""

    def __init__(
        self, environment: Environment | None = None, auth_provider: AuthProvider | None = None, **kwargs: Any
    ) -> None:
        self.environment = environment or get_environment()
        super().__init__(
            self.environment.api_base_url,
            name="UserClient",
            auth_provider=auth_provider,
            verify_ssl=self.environment.verify_ssl,
            timeout=self.environment.api_timeout_seconds,
            **kwargs,
        )

    def create_user(self, payload: dict[str, Any]) -> ApiResponse:
        """POST <SIGNUP_ENDPOINT> - creates a test account (DATA_CREATING)."""
        return self.post(
            self.environment.endpoint("signup"), json=payload, authenticate=False, artifact_name="user_create"
        )

    def get_user(self, user_id: str) -> ApiResponse:
        """GET <PROFILE_ENDPOINT>/{user_id} - example of a path parameter."""
        return self.get(
            self.environment.endpoint("profile") + "/{user_id}",
            path_params={"user_id": user_id},
            artifact_name="user_get",
        )

    def delete_user(self, user_id: str) -> ApiResponse:
        """DELETE <DELETE_USER_ENDPOINT> - cleanup only (DESTRUCTIVE)."""
        return self.delete(
            self.environment.endpoint("delete_user") + "/{user_id}",
            path_params={"user_id": user_id},
            artifact_name="user_delete",
        )
