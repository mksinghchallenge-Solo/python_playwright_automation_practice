"""
E2E: API setup -> UI verification.

    API creates test user
          ↓
    UI login (through the UI - browser session is NOT the API token)
          ↓
    Open profile
          ↓
    Verify the API-created data is displayed
          ↓
    API cleanup (fixture teardown deletes the user)
"""

import allure
import pytest

from fixtures.e2e_fixtures import E2eActors

pytestmark = [pytest.mark.e2e, pytest.mark.profile, pytest.mark.data_creating]


@allure.feature("E2E")
@allure.story("API setup -> UI verification")
class TestApiSetupUiVerify:
    @allure.title("User created via API can log in via UI and sees API data")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_api_created_user_visible_in_ui(self, e2e_actors: E2eActors) -> None:
        user = e2e_actors.user

        with allure.step("API: confirm the created user exists"):
            api_profile = e2e_actors.profile_api.get_profile()
            assert api_profile.status_code == 200, api_profile.failure_report()
            assert api_profile.json()["email"] == user.email

        e2e_actors.ui_login()

        with allure.step("UI: profile shows the API-created values"):
            e2e_actors.profile_page.expect_signed_in_as(user.email)
            e2e_actors.profile_page.expect_first_name(user.first_name)
            e2e_actors.profile_page.expect_last_name(user.last_name)
            e2e_actors.profile_page.screenshot("e2e_api_to_ui_profile")

    @allure.title("Profile updated via API is reflected in the UI")
    @pytest.mark.regression
    @pytest.mark.data_modifying
    def test_api_update_visible_in_ui(self, e2e_actors: E2eActors) -> None:
        with allure.step("API: update first name"):
            update = e2e_actors.profile_api.update_profile({"first_name": "ApiUpdated"})
            assert update.status_code == 200, update.failure_report()

        e2e_actors.ui_login()

        with allure.step("UI: verify updated first name"):
            e2e_actors.profile_page.expect_first_name("ApiUpdated")
