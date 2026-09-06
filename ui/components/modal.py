"""Generic modal / dialog component."""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from ui.components.base_component import BaseComponent
from utils.common.runtime_context import RuntimeContext
from utils.reporting.allure_manager import step


class Modal(BaseComponent):
    """Interact with any ``role=dialog`` element."""

    def __init__(self, page: Page, context: RuntimeContext, name: str | re.Pattern[str] | None = None) -> None:
        super().__init__(page, context)
        self.dialog: Locator = page.get_by_role("dialog", name=name) if name else page.get_by_role("dialog")
        self.close_button: Locator = self.dialog.get_by_role("button", name=re.compile(r"close|dismiss|×|x$", re.I))

    def is_open(self, timeout_ms: int = 3000) -> bool:
        return self.is_visible(self.dialog, timeout_ms)

    def expect_open(self) -> None:
        with step("Expect modal open"):
            expect(self.dialog.first).to_be_visible()

    def close(self) -> None:
        with step("Close modal"):
            if self.is_visible(self.close_button, 2000):
                self.log.info("Closing modal via close button")
                self.close_button.first.click()
            else:
                self.log.info("No close button - pressing Escape")
                self.page.keyboard.press("Escape")
            expect(self.dialog.first).to_be_hidden()

    def button(self, name: str | re.Pattern[str]) -> Locator:
        return self.dialog.get_by_role("button", name=name)

    def text(self) -> str:
        return (self.dialog.first.text_content() or "").strip()
