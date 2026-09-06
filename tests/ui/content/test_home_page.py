"""
UI tests - home page.

Run against the practice app (``ENV=local``) or the real site (``ENV=qa``).
Expectations come from ``test_data/ui/navigation.yaml`` per environment, so
the test code itself has no environment-specific strings.
"""

import re

import allure
import pytest

from ui.pages.home_page import HomePage
from utils.config.environment_manager import Environment
from utils.data.data_reader import DataReader

pytestmark = [pytest.mark.ui, pytest.mark.content, pytest.mark.read_only]


@allure.feature("Home page")
@allure.story("Landing")
class TestHomePage:
    @allure.title("Home page loads with header, heading and footer")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.description("Opens the base URL, accepts cookies, verifies landmarks and takes a screenshot.")
    @pytest.mark.smoke
    def test_home_page_loads(self, prepared_home: HomePage, environment: Environment) -> None:
        expectations = DataReader.load("ui/navigation.yaml")[environment.name]
        prepared_home.expect_loaded()
        prepared_home.expect_title_contains(expectations["title_contains"])
        prepared_home.navigation.expect_footer_visible()
        prepared_home.screenshot("home_page_loaded")

    @allure.title("Home page has no console errors on load")
    @pytest.mark.regression
    def test_no_severe_console_errors(self, home_page: HomePage) -> None:
        errors: list[str] = []
        home_page.page.on("pageerror", lambda exc: errors.append(str(exc)))
        home_page.open_and_prepare()
        home_page.expect_loaded()
        assert not errors, f"JavaScript errors on home page: {errors}"

    @allure.title("External link opens in a new tab")
    @pytest.mark.regression
    def test_external_link_opens_new_tab(self, prepared_home: HomePage) -> None:
        external = prepared_home.page.get_by_role("link", name=re.compile("new tab|official", re.I)).first
        if not prepared_home.is_visible(external, 2000):
            pytest.skip("No external new-tab link on this environment's home page")
        expected_href = external.get_attribute("href") or ""
        new_tab = prepared_home.click_and_wait_for_new_tab(external, "external link")
        assert new_tab != prepared_home.page, "a new tab should have been opened"
        if new_tab.url.startswith("chrome-error://"):
            new_tab.close()
            pytest.skip(f"External site {expected_href} unreachable from this network")
        assert new_tab.url.startswith(expected_href.rstrip("/")[:30]), f"unexpected new tab URL {new_tab.url}"
        new_tab.close()
