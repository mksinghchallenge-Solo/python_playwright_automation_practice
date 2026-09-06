"""UI tests - account creation (DATA_CREATING; blocked on prod by the safety guard)."""

import allure
import pytest

from ui.pages.profile_page import ProfilePage
from ui.pages.signup_page import SignupPage
from utils.data.test_data_factory import TestUser

pytestmark = [pytest.mark.ui, pytest.mark.auth, pytest.mark.data_creating]


@allure.feature("Authentication UI")
@allure.story("Signup")
class TestSignupUi:
    @allure.title("New user can create an account")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.regression
    def test_signup_success(self, signup_page: SignupPage, profile_page: ProfilePage, generated_user: TestUser) -> None:
        signup_page.open_and_prepare()
        signup_page.expect_loaded()
        signup_page.sign_up(generated_user)
        profile_page.expect_loaded()
        profile_page.expect_signed_in_as(generated_user.email)
        profile_page.expect_first_name(generated_user.first_name)
        profile_page.screenshot("test_signup_success")

    @allure.title("Duplicate email is rejected")
    @pytest.mark.negative
    @pytest.mark.regression
    def test_signup_duplicate_email(
        self, signup_page: SignupPage, profile_page: ProfilePage, generated_user: TestUser
    ) -> None:
        signup_page.open_and_prepare()
        signup_page.sign_up(generated_user)
        profile_page.expect_loaded()
        profile_page.sign_out()
        signup_page.open_and_prepare()
        signup_page.sign_up(generated_user)
        signup_page.expect_error("already exists")
