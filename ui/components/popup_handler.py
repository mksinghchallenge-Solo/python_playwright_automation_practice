"""
Popup / overlay handler.

Marketing sites show newsletter overlays, geo prompts, promo dialogs and
native ``alert``/``confirm`` dialogs. This component centralises dismissing
them so tests stay clean. Every method is tolerant of the popup being absent.
"""

from __future__ import annotations

import re

from playwright.sync_api import Dialog, Locator, Page

from ui.components.base_component import BaseComponent
from utils.common.runtime_context import RuntimeContext
from utils.reporting.allure_manager import step


class PopupHandler(BaseComponent):
    """Dismisses common overlays and auto-handles native dialogs."""

    def __init__(self, page: Page, context: RuntimeContext) -> None:
        super().__init__(page, context)
        self.overlay_close_buttons: Locator = page.get_by_role(
            "button", name=re.compile(r"^(close|dismiss|no thanks|not now|maybe later|×|x)$", re.I)
        )
        self.dialogs: Locator = page.get_by_role("dialog")
        self._auto_dialog_registered = False

    def dismiss_overlays_if_present(self, timeout_ms: int = 1000) -> int:
        """Close visible overlay dialogs. Returns how many were closed."""
        closed = 0
        with step("Dismiss overlays if present"):
            if not self.is_visible(self.overlay_close_buttons, timeout_ms):
                self.log.info("No overlay/popup displayed")
                return 0
            for button in self.overlay_close_buttons.all()[:5]:
                try:
                    if button.is_visible():
                        self.log.info("Closing popup via '%s'", (button.text_content() or "").strip())
                        button.click()
                        closed += 1
                except Exception as exc:
                    self.log.debug("Popup close attempt failed: %s", exc)
        return closed

    def auto_accept_native_dialogs(self) -> None:
        """Automatically accept ``alert``/``confirm``/``prompt`` dialogs."""
        if self._auto_dialog_registered:
            return

        def _handle(dialog: Dialog) -> None:
            self.log.info("Native dialog (%s): %s -> accepting", dialog.type, dialog.message)
            dialog.accept()

        self.page.on("dialog", _handle)
        self._auto_dialog_registered = True

    def auto_dismiss_native_dialogs(self) -> None:
        def _handle(dialog: Dialog) -> None:
            self.log.info("Native dialog (%s): %s -> dismissing", dialog.type, dialog.message)
            dialog.dismiss()

        self.page.on("dialog", _handle)
