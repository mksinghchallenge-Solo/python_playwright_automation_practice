"""
Content client - public content endpoints (pages, products, articles).

``<CONTENT_ENDPOINT>`` is a placeholder. Content endpoints are usually
read-only and unauthenticated, making them ideal first candidates for
API discovery (docs/api_discovery.md).
"""

from __future__ import annotations

from typing import Any

from api.clients.base_client import AuthProvider, BaseAPIClient
from api.models.api_response import ApiResponse
from utils.config.environment_manager import Environment, get_environment


class ContentClient(BaseAPIClient):
    """Read-only content endpoints."""

    def __init__(
        self, environment: Environment | None = None, auth_provider: AuthProvider | None = None, **kwargs: Any
    ) -> None:
        self.environment = environment or get_environment()
        super().__init__(
            self.environment.api_base_url,
            name="ContentClient",
            auth_provider=auth_provider,
            verify_ssl=self.environment.verify_ssl,
            timeout=self.environment.api_timeout_seconds,
            **kwargs,
        )

    def list_content(self, **query: Any) -> ApiResponse:
        """GET <CONTENT_ENDPOINT>?page=..&size=.. (READ_ONLY)."""
        return self.get(
            self.environment.endpoint("content"), params=query or None, authenticate=False, artifact_name="content_list"
        )

    def get_content(self, content_id: str) -> ApiResponse:
        return self.get(
            self.environment.endpoint("content") + "/{content_id}",
            path_params={"content_id": content_id},
            authenticate=False,
            artifact_name="content_get",
        )
