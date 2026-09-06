"""
UI tests - login / logout.

Credentials come from .env (UI_USER_EMAIL / UI_USER_PASSWORD) - never from
code. On environments without a sign-in page the tests skip.

This file is the *result* of the Codegen -> POM conversion described in
docs/codegen_to_pom.md.
"""

import os

import allure
import pytest

from ui.pages.login_page import LoginPage
from ui.pages.profile_page import ProfilePage
from utils.data.data_reader import DataReader

pytestmark = [pytest.mark.ui, pytest.mark.auth, pytest.mark.read_only]
NEGATIVE = DataReader.load("ui/login_negative_cases.csv")


@pytest.fixture
def ui_credentials() -> tuple[str, str]:
    email, password = os.getenv("UI_USER_EMAIL", ""), os.getenv("UI_USER_PASSWORD", "")
    if not email or not password:
        pytest.skip("UI_USER_EMAIL / UI_USER_PASSWORD not set in .env")
    return email, password


@allure.feature("Authentication UI")
@allure.story("Login")
class TestLoginUi:
    @allure.title("Valid user can sign in and sees the profile")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_login_success(
        self, login_page: LoginPage, profile_page: ProfilePage, ui_credentials: tuple[str, str]
    ) -> None:
        email, password = ui_credentials
        login_page.open_and_prepare()
        login_page.expect_loaded()
        login_page.login(email, password)
        profile_page.expect_loaded()
        profile_page.expect_signed_in_as(email)
        profile_page.screenshot("test_login_success")

    @allure.title("Login rejected: {case[id]}")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.parametrize("case", NEGATIVE, ids=[c["id"] for c in NEGATIVE])
    def test_login_negative(self, login_page: LoginPage, case: dict) -> None:
        login_page.open_and_prepare()
        login_page.login(case["email"], case["password"])
        login_page.expect_error(case["expected_error"])
        login_page.screenshot(f"test_login_failure_{case['id']}")


@allure.feature("Authentication UI")
@allure.story("Logout")
class TestLogoutUi:
    @allure.title("Signed-in user can sign out")
    @pytest.mark.regression
    def test_logout(self, login_page: LoginPage, profile_page: ProfilePage, ui_credentials: tuple[str, str]) -> None:
        email, password = ui_credentials
        login_page.open_and_prepare()
        login_page.login(email, password)
        profile_page.expect_loaded()
        profile_page.sign_out()
        # After logout the profile page must not be reachable.
        profile_page.open()
        login_page.expect_loaded()
