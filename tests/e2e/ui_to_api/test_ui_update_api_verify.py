"""
E2E: UI action -> API verification.

    API creates test user (setup)
          ↓
    UI login + edit profile
          ↓
    API GET profile
          ↓
    Verify backend state matches what the UI saved
          ↓
    API cleanup
"""

import allure
import pytest

from api.validators.response_validator import ResponseValidator
from api.validators.schema_validator import SchemaValidator
from fixtures.e2e_fixtures import E2eActors
from ui.pages.edit_profile_page import EditProfilePage
from utils.data.test_data_factory import TestDataFactory

pytestmark = [pytest.mark.e2e, pytest.mark.profile, pytest.mark.data_modifying]


@allure.feature("E2E")
@allure.story("UI update -> API verification")
class TestUiUpdateApiVerify:
    @allure.title("Profile edited in UI is persisted in the backend")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_ui_edit_persisted_via_api(self, e2e_actors: E2eActors, edit_profile_page: EditProfilePage) -> None:
        new_values = TestDataFactory.profile_update_payload()

        e2e_actors.ui_login()

        with allure.step("UI: edit profile"):
            e2e_actors.profile_page.go_to_edit()
            edit_profile_page.expect_loaded()
            edit_profile_page.update(**new_values)
            e2e_actors.profile_page.expect_loaded()
            e2e_actors.profile_page.expect_first_name(new_values["first_name"])

        with allure.step("API: verify backend state"):
            response = e2e_actors.profile_api.get_profile()
            validator = ResponseValidator(response).status(200)
            for key, value in new_values.items():
                validator.field_equals(key, value)
            SchemaValidator.validate_response(response, "api/profile_schema.json")
