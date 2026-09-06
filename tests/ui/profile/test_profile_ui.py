"""UI tests - view and edit profile."""

import allure
import pytest

from ui.pages.edit_profile_page import EditProfilePage
from ui.pages.login_page import LoginPage
from ui.pages.profile_page import ProfilePage
from ui.pages.signup_page import SignupPage
from utils.data.test_data_factory import TestDataFactory, TestUser

pytestmark = [pytest.mark.ui, pytest.mark.profile]


@pytest.fixture
def signed_in_user(signup_page: SignupPage, profile_page: ProfilePage, generated_user: TestUser) -> TestUser:
    """Create a fresh user through the UI so edits never touch shared accounts."""
    signup_page.open_and_prepare()
    signup_page.sign_up(generated_user)
    profile_page.expect_loaded()
    return generated_user


@allure.feature("Profile UI")
class TestProfileUi:
    @allure.title("Profile page shows the user's data")
    @pytest.mark.smoke
    @pytest.mark.data_creating
    def test_view_profile(self, profile_page: ProfilePage, signed_in_user: TestUser) -> None:
        data = profile_page.profile_data()
        assert data["email"] == signed_in_user.email
        assert data["first_name"] == signed_in_user.first_name
        profile_page.screenshot("profile_view")

    @allure.title("User can edit first name and zip code")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.regression
    @pytest.mark.data_modifying
    def test_edit_profile(
        self, profile_page: ProfilePage, edit_profile_page: EditProfilePage, signed_in_user: TestUser
    ) -> None:
        new_values = TestDataFactory.profile_update_payload()
        profile_page.go_to_edit()
        edit_profile_page.expect_loaded()
        edit_profile_page.update(first_name=new_values["first_name"], zip_code=new_values["zip_code"])
        profile_page.expect_loaded()
        profile_page.expect_first_name(new_values["first_name"])
        profile_page.expect_zip(new_values["zip_code"])
        profile_page.screenshot("test_profile_update_success")

    @allure.title("Profile requires authentication")
    @pytest.mark.regression
    @pytest.mark.read_only
    def test_profile_requires_login(self, profile_page: ProfilePage, login_page: LoginPage) -> None:
        profile_page.open()
        login_page.expect_loaded()
