"""
MOCKED API tests - exercise clients/validators against a local mock server.

Marked ``mocked`` so they are excluded from real integration runs:
    pytest -m "api and not mocked"        # real only
    pytest -m mocked                      # mocks only
"""

import allure
import pytest

from api.clients.auth_client import StaticTokenProvider
from api.clients.base_client import BaseAPIClient
from api.mocks.mock_server import MockApiServer
from api.validators.response_validator import ResponseValidator
from api.validators.schema_validator import SchemaValidator

pytestmark = [pytest.mark.api, pytest.mark.mocked, pytest.mark.read_only]


@allure.feature("Profile API (mocked)")
class TestMockedProfile:
    @allure.title("Mocked profile passes schema + validator chain")
    def test_mocked_profile_happy_path(self, mock_server: MockApiServer) -> None:
        mock_server.add_route(
            "GET",
            "/api/users/me",
            200,
            {"id": "u-1", "email": "mock@example.com", "first_name": "Mock", "last_name": "User"},
        )
        client = BaseAPIClient(mock_server.base_url, auth_provider=StaticTokenProvider("mock-token"))
        response = client.get("/api/users/me")
        ResponseValidator(response).status(200).field_equals("email", "mock@example.com")
        SchemaValidator.validate_response(response, "api/profile_schema.json")
        assert mock_server.requests_for("GET", "/api/users/me")[0].headers["Authorization"] == "Bearer mock-token"

    @allure.title("Mocked 429 / 503 are surfaced (not swallowed)")
    @pytest.mark.parametrize("status", [429, 503])
    def test_mocked_error_statuses(self, mock_server: MockApiServer, status: int) -> None:
        mock_server.add_route("GET", "/api/users/me", status, {"error": "unavailable"})
        response = BaseAPIClient(mock_server.base_url, max_retries=0).get("/api/users/me")
        ResponseValidator(response).status(status)

    @allure.title("Mocked schema violation is reported with field paths")
    def test_mocked_schema_violation(self, mock_server: MockApiServer) -> None:
        mock_server.add_route("GET", "/api/users/me", 200, {"id": 123, "email": "not-an-email"})
        response = BaseAPIClient(mock_server.base_url).get("/api/users/me")
        with pytest.raises(AssertionError) as excinfo:
            SchemaValidator.validate_response(response, "api/profile_schema.json")
        assert "first_name" in str(excinfo.value)
