"""
Main site navigation component (header, menu, search, footer links).

Selectors favour accessible roles so they survive CSS refactors.
"""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from ui.components.base_component import BaseComponent
from utils.common.runtime_context import RuntimeContext
from utils.reporting.allure_manager import step


class Navigation(BaseComponent):
    """Header/menu/footer navigation."""

    def __init__(self, page: Page, context: RuntimeContext) -> None:
        super().__init__(page, context)
        self.header: Locator = page.get_by_role("banner").or_(page.locator("header")).first
        self.footer: Locator = page.get_by_role("contentinfo").or_(page.locator("footer")).first
        self.logo_link: Locator = self.header.get_by_role("link", name=re.compile("coca.?cola", re.I)).first
        self.menu_button: Locator = self.header.get_by_role(
            "button", name=re.compile(r"menu|open navigation|navigation", re.I)
        ).first
        self.search_button: Locator = self.header.get_by_role("button", name=re.compile("search", re.I)).first
        self.search_input: Locator = (
            page.get_by_role("searchbox").or_(page.get_by_placeholder(re.compile("search", re.I))).first
        )
        self.nav_links: Locator = page.get_by_role("navigation").get_by_role("link")

    def expect_header_visible(self) -> None:
        with step("Expect site header visible"):
            expect(self.header).to_be_visible()

    def expect_footer_visible(self) -> None:
        with step("Expect site footer visible"):
            self.footer.scroll_into_view_if_needed()
            expect(self.footer).to_be_visible()

    def open_menu(self) -> None:
        """Open the hamburger/mega menu when it exists (mobile + desktop)."""
        with step("Open main menu"):
            if self.is_visible(self.menu_button, 3000):
                self.log.info("Opening main menu")
                self.menu_button.click()
            else:
                self.log.info("Menu button not present (menu likely always expanded)")

    def click_link(self, name: str | re.Pattern[str]) -> None:
        with step(f"Click navigation link '{name}'"):
            self.log.info("Clicking navigation link %s", name)
            self.page.get_by_role("link", name=name).first.click()

    def visible_link_texts(self, limit: int = 50) -> list[str]:
        texts: list[str] = []
        for link in self.nav_links.all()[:limit]:
            try:
                if link.is_visible():
                    text = (link.text_content() or "").strip()
                    if text:
                        texts.append(text)
            except Exception:
                continue
        return texts

    def search(self, term: str) -> None:
        with step(f"Search for '{term}'"):
            if self.is_visible(self.search_button, 3000):
                self.search_button.click()
            self.log.info("Searching for %s", term)
            self.search_input.fill(term)
            self.search_input.press("Enter")
