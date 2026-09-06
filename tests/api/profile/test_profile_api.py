"""API tests - profile (GET / PUT) using the authenticated ProfileClient."""

import allure
import pytest

from api.clients.profile_client import ProfileClient
from api.validators.response_validator import ResponseValidator
from api.validators.schema_validator import SchemaValidator
from utils.data.data_reader import DataReader
from utils.data.test_data_factory import TestDataFactory

pytestmark = [pytest.mark.api, pytest.mark.profile]
PAYLOADS = DataReader.load("api/profile_update_payloads.yaml")


@allure.feature("Profile API")
@allure.story("Get profile")
class TestGetProfile:
    @allure.title("Authenticated user can read own profile")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    @pytest.mark.read_only
    def test_get_profile(self, profile_client: ProfileClient, api_credentials: tuple[str, str]) -> None:
        email, _ = api_credentials
        response = profile_client.get_profile()
        (
            ResponseValidator(response)
            .status(200)
            .content_type("application/json")
            .correlation_id_present()
            .cache_control_present()
            .security_headers_present(strict=False)
            .field_equals("email", email)
            .field_not_null("id")
            .field_absent("password")
        )
        SchemaValidator.validate_response(response, "api/profile_schema.json")


@allure.feature("Profile API")
@allure.story("Update profile")
class TestUpdateProfile:
    @allure.title("Update profile and verify with a follow-up GET")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.regression
    @pytest.mark.data_modifying
    def test_update_then_get(self, profile_client: ProfileClient) -> None:
        original = profile_client.get_profile().json()
        payload = TestDataFactory.profile_update_payload()
        try:
            update = profile_client.update_profile(payload)
            ResponseValidator(update).status(200)
            for key, value in payload.items():
                ResponseValidator(update).field_equals(key, value)

            fetched = profile_client.get_profile()
            for key, value in payload.items():
                ResponseValidator(fetched).field_equals(key, value)
        finally:
            # cleanup: restore original values so other tests are unaffected
            profile_client.update_profile(
                {k: original[k] for k in ("first_name", "last_name", "zip_code") if k in original}
            )

    @allure.title("Partial update keeps other fields")
    @pytest.mark.regression
    @pytest.mark.data_modifying
    def test_partial_update(self, profile_client: ProfileClient) -> None:
        before = profile_client.get_profile().json()
        response = profile_client.update_profile(PAYLOADS["valid_partial"])
        try:
            (
                ResponseValidator(response)
                .status(200)
                .field_equals("zip_code", PAYLOADS["valid_partial"]["zip_code"])
                .field_equals("first_name", before["first_name"])
            )
        finally:
            profile_client.update_profile({"zip_code": before.get("zip_code", "")})

    @allure.title("Unknown field is rejected")
    @pytest.mark.negative
    @pytest.mark.read_only
    def test_unknown_field_rejected(self, profile_client: ProfileClient) -> None:
        response = profile_client.update_profile(PAYLOADS["invalid_unknown_field"])
        ResponseValidator(response).status_in([400, 422])
