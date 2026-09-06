"""
LoginPage - sign-in form.

Locators use labels/placeholders first (Playwright's recommendation) so the
same Page Object works for the practice app and, after you adjust the
labels, for the real sign-in page discovered with Codegen.
See docs/codegen_to_pom.md for the exact conversion walk-through.
"""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from ui.components.cookie_banner import CookieBanner
from ui.pages.base_page import BasePage
from utils.common.runtime_context import RuntimeContext
from utils.data.test_data_factory import TestUser
from utils.reporting.allure_manager import step


class LoginPage(BasePage):
    PATH = "login"

    def __init__(self, page: Page, context: RuntimeContext) -> None:
        super().__init__(page, context)
        self.cookie_banner = CookieBanner(page, context)
        self.email_input: Locator = (
            page.get_by_label(re.compile(r"email", re.I)).or_(page.get_by_placeholder(re.compile(r"email", re.I))).first
        )
        self.password_input: Locator = (
            page.get_by_label(re.compile(r"^password", re.I))
            .or_(page.get_by_placeholder(re.compile(r"password", re.I)))
            .first
        )
        self.submit_button: Locator = page.get_by_role(
            "button", name=re.compile(r"^(sign in|log in|login|continue)$", re.I)
        ).first
        self.error_message: Locator = page.get_by_role("alert").or_(page.locator(".error")).first
        self.create_account_link: Locator = page.get_by_role(
            "link", name=re.compile(r"create account|sign up|register", re.I)
        ).first

    # -------------------------------------------------------------- flows
    def open_and_prepare(self) -> LoginPage:
        self.open()
        self.cookie_banner.accept_if_present()
        return self

    def login(self, email: str, password: str) -> None:
        """Fill credentials and submit. The password is masked in logs/Allure."""
        with step(f"Login as {email}"):
            self.fill(self.email_input, email, "email")
            self.fill(self.password_input, password, "password", secret=True)
            self.click(self.submit_button, "Sign in button")

    def login_as(self, user: TestUser) -> None:
        self.login(user.email, user.password)

    # --------------------------------------------------------- assertions
    def expect_loaded(self) -> None:
        with step("Expect login page loaded"):
            expect(self.email_input).to_be_visible()
            expect(self.password_input).to_be_visible()
            expect(self.submit_button).to_be_visible()

    def expect_error(self, text: str | re.Pattern[str] | None = None) -> None:
        with step("Expect login error message"):
            expect(self.error_message).to_be_visible()
            if text is not None:
                expect(self.error_message).to_contain_text(text)

    def error_text(self) -> str:
        return self.text_of(self.error_message)
