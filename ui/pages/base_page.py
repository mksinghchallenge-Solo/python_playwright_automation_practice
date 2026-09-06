"""
BasePage - parent of every Page Object.

Provides the small set of things *all* pages need:

* navigation relative to the environment base URL
* logged, auto-waiting wrappers around common actions
* screenshot helper wired into the artifact manager + Allure
* access to shared components (cookie banner, navigation, popups)

Page Objects should expose *business actions* (``login(user)``) built from
these primitives, never raw selectors to tests.

Locator strategy priority (Playwright recommendation)::

    get_by_role > get_by_label > get_by_placeholder > get_by_test_id > get_by_text > CSS > XPath

IMPORTANT: this module never performs HTTP requests itself. Backend
verification belongs to the API layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Locator, Page, expect

from utils.artifacts.artifact_manager import get_artifact_manager
from utils.common.helpers import join_url
from utils.common.runtime_context import RuntimeContext
from utils.logging.logger import get_logger
from utils.reporting.allure_manager import attach_file, step


class BasePage:
    """Common behaviour for all Page Objects."""

    # Relative path of the page, overridden by subclasses ("" == base URL).
    PATH: str = ""

    def __init__(self, page: Page, context: RuntimeContext) -> None:
        self.page = page
        self.context = context
        self.base_url = context.ui_base_url
        self.log = get_logger(self.__class__.__name__)

    # ---------------------------------------------------------- navigation
    def url_for(self, path: str | None = None) -> str:
        return join_url(self.base_url, self.PATH if path is None else path)

    def open(self, path: str | None = None, wait_until: str = "domcontentloaded") -> BasePage:
        """Navigate to this page (or ``path``) and return ``self`` for chaining."""
        url = self.url_for(path)
        with step(f"Open {url}"):
            self.log.info("Navigating to %s", url)
            self.page.goto(url, wait_until=wait_until)  # type: ignore[arg-type]
        return self

    def reload(self) -> None:
        self.log.info("Reloading %s", self.page.url)
        self.page.reload(wait_until="domcontentloaded")

    @property
    def current_url(self) -> str:
        return self.page.url

    @property
    def title(self) -> str:
        return self.page.title()

    # ------------------------------------------------------------- actions
    def click(self, locator: Locator, description: str) -> None:
        with step(f"Click {description}"):
            self.log.info("Clicking %s", description)
            locator.click()

    def fill(self, locator: Locator, value: str, description: str, secret: bool = False) -> None:
        shown = "*****" if secret else value
        with step(f"Fill {description}"):
            self.log.info("Entering %s: %s", description, shown)
            locator.fill(value)

    def select(self, locator: Locator, value: str, description: str) -> None:
        with step(f"Select '{value}' in {description}"):
            self.log.info("Selecting %s in %s", value, description)
            locator.select_option(value)

    def check(self, locator: Locator, description: str) -> None:
        with step(f"Check {description}"):
            self.log.info("Checking %s", description)
            locator.check()

    def press(self, locator: Locator, key: str, description: str) -> None:
        with step(f"Press {key} on {description}"):
            self.log.info("Pressing %s on %s", key, description)
            locator.press(key)

    def hover(self, locator: Locator, description: str) -> None:
        with step(f"Hover {description}"):
            self.log.info("Hovering %s", description)
            locator.hover()

    def text_of(self, locator: Locator) -> str:
        return (locator.text_content() or "").strip()

    # --------------------------------------------------------- assertions
    def expect_visible(self, locator: Locator, description: str, timeout: int | None = None) -> None:
        with step(f"Expect {description} visible"):
            self.log.info("Expecting %s to be visible", description)
            expect(locator).to_be_visible(timeout=timeout)

    def expect_url_contains(self, fragment: str, timeout: int | None = None) -> None:
        with step(f"Expect URL contains '{fragment}'"):
            self.log.info("Expecting URL to contain '%s'", fragment)
            expect(self.page).to_have_url(
                f"**{fragment}**" if not fragment.startswith("http") else fragment, timeout=timeout
            )

    def expect_title_contains(self, fragment: str, timeout: int | None = None) -> None:
        import re

        with step(f"Expect title contains '{fragment}'"):
            expect(self.page).to_have_title(re.compile(re.escape(fragment), re.IGNORECASE), timeout=timeout)

    def is_visible(self, locator: Locator, timeout_ms: int = 3000) -> bool:
        """Non-throwing visibility probe for optional elements (popups, banners)."""
        try:
            locator.first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            return False

    # -------------------------------------------------------- screenshots
    def screenshot(self, name: str, full_page: bool | None = None) -> Path:
        """Capture, store under ui/screenshots and attach to Allure."""
        from utils.config.config_reader import get_config

        artifacts = get_artifact_manager()
        path = artifacts.screenshot_path(name, self.context.browser_label, self.context.device_label)
        full = get_config().get("artifacts.screenshot_full_page", True) if full_page is None else full_page
        try:
            self.page.screenshot(path=str(path), full_page=bool(full))
        except Exception as exc:  # full-page can fail on very long pages
            self.log.warning("Full-page screenshot failed (%s); retrying viewport only", exc)
            self.page.screenshot(path=str(path), full_page=False)
        self.log.info("Screenshot saved: %s", path)
        attach_file(path, name=path.name)
        return path

    # ------------------------------------------------------------ windows
    def click_and_wait_for_new_tab(self, locator: Locator, description: str) -> Page:
        """Click something that opens a new tab and return the new Page."""
        with step(f"Click {description} (expects new tab)"):
            self.log.info("Clicking %s and waiting for new tab", description)
            with self.page.context.expect_page() as new_page_info:
                locator.click()
            new_page = new_page_info.value
            new_page.wait_for_load_state("domcontentloaded")
            self.log.info("New tab opened: %s", new_page.url)
            return new_page

    def evaluate(self, script: str, arg: Any = None) -> Any:
        return self.page.evaluate(script, arg)
