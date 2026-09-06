"""API tests - authentication (negative + data-driven + unsupported method)."""

import allure
import pytest

from api.clients.auth_client import AuthClient
from api.validators.response_validator import ResponseValidator
from api.validators.schema_validator import SchemaValidator
from utils.data.data_reader import DataReader

pytestmark = [pytest.mark.api, pytest.mark.auth, pytest.mark.negative, pytest.mark.read_only]

NEGATIVE_CASES = DataReader.parametrize_cases("api/login_negative_cases.json")


@allure.feature("Authentication API")
@allure.story("Login - negative")
class TestLoginNegative:
    @allure.title("Login rejected: {case[id]}")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.regression
    @pytest.mark.parametrize("case", NEGATIVE_CASES, ids=DataReader.case_ids(NEGATIVE_CASES))
    def test_login_rejected(self, auth_client: AuthClient, case: dict) -> None:
        response = auth_client.login_raw(case["payload"])
        (
            ResponseValidator(response)
            .status(case["expected_status"])
            .content_type("application/json")
            .field_absent("access_token")
        )
        SchemaValidator.validate_response(response, "api/error_schema.json")

    @allure.title("Malformed JSON body is rejected with 400")
    def test_malformed_json(self, auth_client: AuthClient) -> None:
        response = auth_client.login_raw('{"email": "x@y.z", "password": ')
        ResponseValidator(response).status(400).field_absent("access_token")

    @allure.title("Unsupported HTTP method on login endpoint")
    def test_unsupported_method(self, auth_client: AuthClient) -> None:
        response = auth_client.get(auth_client.environment.endpoint("login"), authenticate=False)
        ResponseValidator(response).status_in([404, 405])

    @allure.title("Very large payload does not crash the endpoint")
    @pytest.mark.boundary
    def test_large_payload(self, auth_client: AuthClient) -> None:
        response = auth_client.login_raw({"email": "x" * 5000 + "@example.com", "password": "y" * 5000})
        ResponseValidator(response).status_in([400, 401, 413, 422]).field_absent("access_token")
