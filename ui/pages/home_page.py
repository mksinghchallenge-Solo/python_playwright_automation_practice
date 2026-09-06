"""
HomePage - the landing page (``/us/en`` on coca-cola.com, ``/`` on the practice app).

Only *generic, resilient* locators are used (roles + landmarks) because the
marketing home page changes often. Brand-specific checks live in tests via
test data, not in the Page Object.
"""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from ui.components.cookie_banner import CookieBanner
from ui.components.navigation import Navigation
from ui.components.popup_handler import PopupHandler
from ui.pages.base_page import BasePage
from utils.common.runtime_context import RuntimeContext
from utils.reporting.allure_manager import step


class HomePage(BasePage):
    PATH = ""

    def __init__(self, page: Page, context: RuntimeContext) -> None:
        super().__init__(page, context)
        self.cookie_banner = CookieBanner(page, context)
        self.navigation = Navigation(page, context)
        self.popups = PopupHandler(page, context)
        self.main: Locator = page.get_by_role("main").or_(page.locator("main")).first
        self.headings: Locator = page.get_by_role("heading")
        self.links: Locator = page.get_by_role("link")
        self.sign_in_link: Locator = page.get_by_role("link", name=re.compile(r"sign in|log in|login", re.I)).first
        self.create_account_link: Locator = page.get_by_role(
            "link", name=re.compile(r"create account|sign up|register|join", re.I)
        ).first

    # -------------------------------------------------------------- flows
    def open_and_prepare(self) -> HomePage:
        """Open, accept cookies, dismiss popups - the standard entry point."""
        self.open()
        self.popups.auto_accept_native_dialogs()
        self.cookie_banner.accept_if_present()
        self.popups.dismiss_overlays_if_present()
        return self

    def go_to_sign_in(self) -> None:
        self.click(self.sign_in_link, "Sign in link")

    def go_to_create_account(self) -> None:
        self.click(self.create_account_link, "Create account link")

    # --------------------------------------------------------- assertions
    def expect_loaded(self) -> None:
        with step("Expect home page loaded"):
            self.log.info("Verifying home page loaded: %s", self.page.url)
            expect(self.page).to_have_url(re.compile(re.escape(self.base_url.rstrip("/")) + r"/?.*"))
            self.navigation.expect_header_visible()
            expect(self.headings.first).to_be_visible()

    def heading_texts(self, limit: int = 20) -> list[str]:
        texts = []
        for heading in self.headings.all()[:limit]:
            try:
                text = (heading.text_content() or "").strip()
                if text:
                    texts.append(text)
            except Exception:
                continue
        return texts

    def all_link_hrefs(self) -> list[str]:
        """Absolute hrefs of every anchor - input for the broken-link checker."""
        return self.page.evaluate("() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)")
