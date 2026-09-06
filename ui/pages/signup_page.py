"""SignupPage - account registration form."""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from ui.components.cookie_banner import CookieBanner
from ui.pages.base_page import BasePage
from utils.common.runtime_context import RuntimeContext
from utils.data.test_data_factory import TestUser
from utils.reporting.allure_manager import step


class SignupPage(BasePage):
    PATH = "signup"

    def __init__(self, page: Page, context: RuntimeContext) -> None:
        super().__init__(page, context)
        self.cookie_banner = CookieBanner(page, context)
        self.first_name_input: Locator = page.get_by_label(re.compile(r"first name", re.I)).first
        self.last_name_input: Locator = page.get_by_label(re.compile(r"last name", re.I)).first
        self.email_input: Locator = page.get_by_label(re.compile(r"email", re.I)).first
        self.password_input: Locator = page.get_by_label(re.compile(r"^password", re.I)).first
        self.zip_input: Locator = page.get_by_label(re.compile(r"zip|postal", re.I)).first
        self.submit_button: Locator = page.get_by_role(
            "button", name=re.compile(r"create account|sign up|register|join", re.I)
        ).first
        self.error_message: Locator = page.get_by_role("alert").or_(page.locator(".error")).first

    def open_and_prepare(self) -> SignupPage:
        self.open()
        self.cookie_banner.accept_if_present()
        return self

    def fill_form(self, user: TestUser) -> None:
        with step(f"Fill signup form for {user.email}"):
            self.fill(self.first_name_input, user.first_name, "first name")
            self.fill(self.last_name_input, user.last_name, "last name")
            self.fill(self.email_input, user.email, "email")
            self.fill(self.password_input, user.password, "password", secret=True)
            if self.is_visible(self.zip_input, 1000):
                self.fill(self.zip_input, user.zip_code, "zip code")

    def submit(self) -> None:
        self.click(self.submit_button, "Create account button")

    def sign_up(self, user: TestUser) -> None:
        self.fill_form(user)
        self.submit()

    def expect_loaded(self) -> None:
        with step("Expect signup page loaded"):
            expect(self.email_input).to_be_visible()
            expect(self.submit_button).to_be_visible()

    def expect_error(self, text: str | re.Pattern[str] | None = None) -> None:
        with step("Expect signup error"):
            expect(self.error_message).to_be_visible()
            if text is not None:
                expect(self.error_message).to_contain_text(text)
