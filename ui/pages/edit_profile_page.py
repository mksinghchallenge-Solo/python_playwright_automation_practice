"""EditProfilePage - form to change profile fields."""

from __future__ import annotations

import re
from typing import Any

from playwright.sync_api import Locator, Page, expect

from ui.pages.base_page import BasePage
from utils.common.runtime_context import RuntimeContext
from utils.reporting.allure_manager import step


class EditProfilePage(BasePage):
    PATH = "profile/edit"

    def __init__(self, page: Page, context: RuntimeContext) -> None:
        super().__init__(page, context)
        self.first_name_input: Locator = page.get_by_label(re.compile(r"first name", re.I)).first
        self.last_name_input: Locator = page.get_by_label(re.compile(r"last name", re.I)).first
        self.zip_input: Locator = page.get_by_label(re.compile(r"zip|postal", re.I)).first
        self.save_button: Locator = page.get_by_role("button", name=re.compile(r"save", re.I)).first
        self.heading: Locator = page.get_by_role("heading", name=re.compile(r"edit profile", re.I)).first

    def expect_loaded(self) -> None:
        with step("Expect edit profile page loaded"):
            expect(self.heading).to_be_visible()
            expect(self.save_button).to_be_visible()

    def update(self, **fields: Any) -> None:
        """Update any of ``first_name`` / ``last_name`` / ``zip_code`` then save."""
        with step(f"Update profile fields {list(fields)}"):
            mapping = {
                "first_name": (self.first_name_input, "first name"),
                "last_name": (self.last_name_input, "last name"),
                "zip_code": (self.zip_input, "zip code"),
            }
            for key, value in fields.items():
                if key not in mapping:
                    raise ValueError(f"Unknown profile field '{key}'. Supported: {list(mapping)}")
                locator, description = mapping[key]
                self.fill(locator, str(value), description)
            self.click(self.save_button, "Save changes button")
