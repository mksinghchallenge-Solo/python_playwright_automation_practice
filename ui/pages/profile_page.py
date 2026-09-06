"""ProfilePage - read-only view of the signed-in user's profile."""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from ui.pages.base_page import BasePage
from utils.common.runtime_context import RuntimeContext
from utils.reporting.allure_manager import step


class ProfilePage(BasePage):
    PATH = "profile"

    def __init__(self, page: Page, context: RuntimeContext) -> None:
        super().__init__(page, context)
        # get_by_test_id is the most stable choice for data-display elements.
        self.first_name: Locator = page.get_by_test_id("profile-first-name")
        self.last_name: Locator = page.get_by_test_id("profile-last-name")
        self.email: Locator = page.get_by_test_id("profile-email")
        self.zip_code: Locator = page.get_by_test_id("profile-zip")
        self.current_user: Locator = page.get_by_test_id("current-user")
        self.edit_button: Locator = (
            page.get_by_role("button", name=re.compile("edit profile", re.I))
            .or_(page.get_by_role("link", name=re.compile("edit profile", re.I)))
            .first
        )
        self.sign_out_link: Locator = page.get_by_role("link", name=re.compile(r"sign out|log out|logout", re.I)).first
        self.heading: Locator = page.get_by_role("heading", name=re.compile(r"profile", re.I)).first

    def expect_loaded(self) -> None:
        with step("Expect profile page loaded"):
            expect(self.heading).to_be_visible()
            expect(self.email).to_be_visible()

    def expect_signed_in_as(self, email: str) -> None:
        with step(f"Expect signed in as {email}"):
            expect(self.current_user).to_have_text(email)

    def expect_first_name(self, value: str) -> None:
        with step(f"Expect first name '{value}'"):
            expect(self.first_name).to_have_text(value)

    def expect_last_name(self, value: str) -> None:
        with step(f"Expect last name '{value}'"):
            expect(self.last_name).to_have_text(value)

    def expect_zip(self, value: str) -> None:
        with step(f"Expect zip '{value}'"):
            expect(self.zip_code).to_have_text(value)

    def profile_data(self) -> dict[str, str]:
        return {
            "first_name": self.text_of(self.first_name),
            "last_name": self.text_of(self.last_name),
            "email": self.text_of(self.email),
            "zip_code": self.text_of(self.zip_code),
        }

    def go_to_edit(self) -> None:
        self.click(self.edit_button, "Edit profile button")

    def sign_out(self) -> None:
        self.click(self.sign_out_link, "Sign out link")
