"""API tests - profile without / with invalid authentication."""

import allure
import pytest

from api.clients.profile_client import ProfileClient
from api.validators.response_validator import ResponseValidator
from utils.config.environment_manager import Environment

pytestmark = [pytest.mark.api, pytest.mark.profile, pytest.mark.negative, pytest.mark.read_only]


@allure.feature("Profile API")
@allure.story("Authorization - negative")
class TestProfileAuthNegative:
    @allure.title("Invalid token is rejected with 401")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_invalid_token(self, invalid_token_profile_client: ProfileClient) -> None:
        response = invalid_token_profile_client.get_profile()
        ResponseValidator(response).status(401).field_absent("email")

    @allure.title("Missing token is rejected with 401")
    def test_missing_token(self, environment: Environment, invalid_token_profile_client: ProfileClient) -> None:
        response = invalid_token_profile_client.get(environment.endpoint("profile"), authenticate=False)
        ResponseValidator(response).status(401)

    @allure.title("Update without token is rejected")
    def test_update_without_token(self, environment: Environment, invalid_token_profile_client: ProfileClient) -> None:
        response = invalid_token_profile_client.put(
            environment.endpoint("update_profile"), json={"first_name": "Hacker"}, authenticate=False
        )
        ResponseValidator(response).status(401)
