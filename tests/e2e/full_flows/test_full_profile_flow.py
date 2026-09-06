"""
E2E full flow: API setup -> UI action -> API validation -> cleanup.

Demonstrates a multi-step business flow with explicit dependency between
steps (allowed here because it IS the workflow under test).
"""

import allure
import pytest

from api.validators.response_validator import ResponseValidator
from fixtures.e2e_fixtures import E2eActors
from ui.pages.edit_profile_page import EditProfilePage
from ui.pages.login_page import LoginPage
from utils.artifacts.artifact_manager import ArtifactManager

pytestmark = [pytest.mark.e2e, pytest.mark.profile, pytest.mark.data_modifying, pytest.mark.regression]


@allure.feature("E2E")
@allure.story("Full flow")
class TestFullProfileFlow:
    @allure.title("Create (API) -> login (UI) -> edit (UI) -> verify (API) -> logout (UI) -> re-login blocked")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_full_flow(
        self,
        e2e_actors: E2eActors,
        edit_profile_page: EditProfilePage,
        login_page: LoginPage,
        artifacts: ArtifactManager,
    ) -> None:
        trail: dict[str, object] = {"user": e2e_actors.user.as_public_dict()}

        with allure.step("1. API: baseline profile"):
            baseline = e2e_actors.profile_api.get_profile().json()
            trail["baseline"] = baseline

        with allure.step("2. UI: login and edit zip code"):
            e2e_actors.ui_login()
            e2e_actors.profile_page.go_to_edit()
            edit_profile_page.update(zip_code="99999")
            e2e_actors.profile_page.expect_zip("99999")

        with allure.step("3. API: verify + other fields unchanged"):
            after = e2e_actors.profile_api.get_profile()
            (
                ResponseValidator(after)
                .status(200)
                .field_equals("zip_code", "99999")
                .field_equals("first_name", baseline["first_name"])
            )
            trail["after"] = after.json()

        with allure.step("4. UI: sign out and confirm profile is protected"):
            e2e_actors.profile_page.sign_out()
            e2e_actors.profile_page.open()
            login_page.expect_loaded()

        artifacts.write_json(artifacts.e2e_path("full_profile_flow_trail"), trail)
