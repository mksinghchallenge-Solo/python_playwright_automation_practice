"""
API tests - authentication (positive).

These run against the endpoint configured as ``api.endpoints.login`` in
``config/environments/<env>.yaml``. On ``local`` that is the practice app;
on qa/staging/prod it is a ``<AUTH_ENDPOINT>`` placeholder and the tests
are skipped automatically until you replace it (docs/api_discovery.md).
"""

import allure
import pytest

from api.clients.auth_client import AuthClient, TokenManager
from api.validators.contract_validator import ContractValidator
from api.validators.response_validator import ResponseValidator
from api.validators.schema_validator import SchemaValidator
from utils.api.api_helpers import assert_response_time

pytestmark = [pytest.mark.api, pytest.mark.auth, pytest.mark.read_only]


@allure.feature("Authentication API")
@allure.story("Login")
class TestLoginApi:
    @allure.title("Valid credentials return an access token")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.description("POST <AUTH_ENDPOINT> with a valid test user; expect 200 + token payload.")
    @pytest.mark.smoke
    def test_login_with_valid_credentials(self, auth_client: AuthClient, api_credentials: tuple[str, str]) -> None:
        email, password = api_credentials
        response = auth_client.login(email, password)

        (
            ResponseValidator(response)
            .status(200)
            .content_type("application/json")
            .field_present("access_token")
            .field_type("access_token", str)
            .field_absent("password")
        )
        SchemaValidator.validate_response(response, "api/auth_token_schema.json")
        assert_response_time(response)

    @allure.title("Login response satisfies the auth contract")
    @pytest.mark.contract
    @pytest.mark.regression
    def test_login_contract(self, auth_client: AuthClient, api_credentials: tuple[str, str]) -> None:
        email, password = api_credentials
        response = auth_client.login(email, password)
        ContractValidator.validate(response, "api/contracts/auth_login_contract.yaml")

    @allure.title("TokenManager caches the token and reuses it")
    @pytest.mark.regression
    def test_token_manager_caches_token(self, auth_client: AuthClient, api_credentials: tuple[str, str]) -> None:
        email, password = api_credentials
        manager = TokenManager(auth_client, email, password)
        first = manager.get_token()
        second = manager.get_token()
        assert first is second, "token should be cached between calls"
        assert manager.auth_headers()["Authorization"].startswith(f"{first.token_type} ")

    @allure.title("TokenManager can force a fresh login")
    @pytest.mark.regression
    def test_token_manager_force_refresh(self, auth_client: AuthClient, api_credentials: tuple[str, str]) -> None:
        email, password = api_credentials
        manager = TokenManager(auth_client, email, password)
        first = manager.get_token()
        second = manager.get_token(force_refresh=True)
        assert first.access_token != second.access_token
