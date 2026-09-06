"""
Example client against a SAFE PUBLIC practice API (httpbin.org).

Purpose: prove that the API layer (base client, logging, masking, artifacts,
validators, schemas) works end-to-end *today*, before real Coca-Cola
endpoints are known. httpbin simply echoes what you send.

This is NOT a Coca-Cola API. Delete this file once your real clients exist.
"""

from __future__ import annotations

import base64
from typing import Any

from api.clients.base_client import AuthProvider, BaseAPIClient
from api.models.api_response import ApiResponse
from utils.config.environment_manager import Environment, get_environment


class ExampleClient(BaseAPIClient):
    """httpbin.org echo endpoints used for framework validation."""

    def __init__(
        self, environment: Environment | None = None, auth_provider: AuthProvider | None = None, **kwargs: Any
    ) -> None:
        self.environment = environment or get_environment()
        super().__init__(
            self.environment.example_api_base_url, name="ExampleClient", auth_provider=auth_provider, **kwargs
        )

    def echo_get(self, **params: Any) -> ApiResponse:
        return self.get("/get", params=params or None, artifact_name="example_get")

    def echo_post(self, payload: dict[str, Any]) -> ApiResponse:
        return self.post("/post", json=payload, artifact_name="example_post")

    def echo_put(self, payload: dict[str, Any]) -> ApiResponse:
        return self.put("/put", json=payload, artifact_name="example_put")

    def echo_patch(self, payload: dict[str, Any]) -> ApiResponse:
        return self.patch("/patch", json=payload, artifact_name="example_patch")

    def echo_delete(self) -> ApiResponse:
        return self.delete("/delete", artifact_name="example_delete")

    def status(self, code: int) -> ApiResponse:
        return self.get("/status/{code}", path_params={"code": code}, artifact_name=f"example_status_{code}")

    def bearer(self) -> ApiResponse:
        """httpbin /bearer returns 200 only when an Authorization: Bearer header is present."""
        return self.get("/bearer", artifact_name="example_bearer")

    def basic_auth(self, user: str, password: str) -> ApiResponse:
        """httpbin /basic-auth/{user}/{password} - demonstrates Basic auth + masking."""
        credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
        return self.get(
            "/basic-auth/{user}/{password}",
            path_params={"user": user, "password": password},
            headers={"Authorization": f"Basic {credentials}"},
            artifact_name="example_basic_auth",
        )

    def delay(self, seconds: int) -> ApiResponse:
        return self.get("/delay/{s}", path_params={"s": seconds}, artifact_name="example_delay")

    def form_post(self, fields: dict[str, str]) -> ApiResponse:
        return self.post("/post", data=fields, artifact_name="example_form")

    def multipart_post(self, files: dict[str, Any]) -> ApiResponse:
        return self.post("/post", files=files, artifact_name="example_multipart")
