"""BaseComponent - parent for reusable page fragments (banner, nav, modal)."""

from __future__ import annotations

from playwright.sync_api import Locator, Page

from utils.common.runtime_context import RuntimeContext
from utils.logging.logger import get_logger


class BaseComponent:
    """A reusable part of a page that is not a page by itself."""

    def __init__(self, page: Page, context: RuntimeContext) -> None:
        self.page = page
        self.context = context
        self.log = get_logger(self.__class__.__name__)

    def is_visible(self, locator: Locator, timeout_ms: int = 3000) -> bool:
        try:
            locator.first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            return False
