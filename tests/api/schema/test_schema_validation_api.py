"""API tests - schema validation across endpoints."""

import allure
import pytest

from api.clients.auth_client import AuthClient
from api.clients.profile_client import ProfileClient
from api.validators.schema_validator import SchemaValidator

pytestmark = [pytest.mark.api, pytest.mark.schema, pytest.mark.read_only]


@allure.feature("Schema validation")
class TestSchemas:
    @allure.title("Profile response matches profile_schema.json")
    @pytest.mark.regression
    def test_profile_schema(self, profile_client: ProfileClient) -> None:
        SchemaValidator.validate_response(profile_client.get_profile(), "api/profile_schema.json")

    @allure.title("Error response matches error_schema.json")
    @pytest.mark.regression
    def test_error_schema(self, auth_client: AuthClient) -> None:
        SchemaValidator.validate_response(auth_client.login("nobody@example.com", "wrong"), "api/error_schema.json")
