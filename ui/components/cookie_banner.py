"""
Cookie consent banner handler.

The Coca-Cola site uses OneTrust for consent management. The banner may or
may not appear depending on region, cookies and A/B experiments, so every
method is *tolerant*: nothing fails when the banner is absent.

Tests never touch this class directly - the ``home_page`` / ``page_context``
fixtures call :meth:`accept_if_present` once after the first navigation.
"""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

from ui.components.base_component import BaseComponent
from utils.common.runtime_context import RuntimeContext
from utils.reporting.allure_manager import step


class CookieBanner(BaseComponent):
    """Handles OneTrust-style cookie consent dialogs."""

    def __init__(self, page: Page, context: RuntimeContext) -> None:
        super().__init__(page, context)
        # Prefer role-based locators; fall back to the well-known OneTrust ids.
        self.accept_button: Locator = page.get_by_role(
            "button", name=re.compile(r"accept all|accept cookies|^accept$|i agree|allow all", re.I)
        ).or_(page.locator("#onetrust-accept-btn-handler"))
        self.reject_button: Locator = page.get_by_role(
            "button", name=re.compile(r"reject all|^reject$|decline|necessary only", re.I)
        ).or_(page.locator("#onetrust-reject-all-handler"))
        self.container: Locator = page.locator("#onetrust-banner-sdk, [id*='cookie'], [class*='cookie-banner']")

    def is_displayed(self, timeout_ms: int = 2500) -> bool:
        return self.is_visible(self.accept_button, timeout_ms)

    def accept_if_present(self, timeout_ms: int = 2500) -> bool:
        """Click *Accept* when the banner is shown. Returns True when clicked."""
        with step("Handle cookie banner (accept if present)"):
            if not self.is_displayed(timeout_ms):
                self.log.info("Cookie banner not displayed - nothing to do")
                return False
            self.log.info("Cookie banner displayed - accepting")
            self.accept_button.first.click()
            try:
                self.accept_button.first.wait_for(state="hidden", timeout=5000)
            except Exception:
                self.log.warning("Cookie banner still visible after accept; continuing")
            return True

    def reject_if_present(self, timeout_ms: int = 2500) -> bool:
        with step("Handle cookie banner (reject if present)"):
            if not self.is_visible(self.reject_button, timeout_ms):
                self.log.info("Cookie reject button not displayed - nothing to do")
                return False
            self.log.info("Cookie banner displayed - rejecting")
            self.reject_button.first.click()
            return True
