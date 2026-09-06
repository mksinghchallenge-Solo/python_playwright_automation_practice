"""UI tests - navigation (header links, menu, page-to-page)."""

import re

import allure
import pytest
from playwright.sync_api import expect

from ui.pages.home_page import HomePage
from utils.config.environment_manager import Environment
from utils.data.data_reader import DataReader

pytestmark = [pytest.mark.ui, pytest.mark.navigation, pytest.mark.read_only]


@allure.feature("Navigation")
class TestNavigation:
    @allure.title("Expected header links are present")
    @pytest.mark.smoke
    def test_header_links_present(self, prepared_home: HomePage, environment: Environment) -> None:
        expected = DataReader.load("ui/navigation.yaml")[environment.name]["header_links"]
        prepared_home.navigation.open_menu()
        for pattern in expected:
            link = prepared_home.page.get_by_role("link", name=re.compile(pattern, re.I)).first
            prepared_home.expect_visible(link, f"link /{pattern}/")

    @allure.title("Navigate to sign-in page from home")
    @pytest.mark.regression
    def test_navigate_to_sign_in(self, prepared_home: HomePage, login_page) -> None:
        prepared_home.navigation.open_menu()
        if not prepared_home.is_visible(prepared_home.sign_in_link, 3000):
            pytest.skip("No sign-in link exposed on this environment")
        prepared_home.go_to_sign_in()
        login_page.expect_loaded()
        login_page.screenshot("sign_in_page_reached")

    @allure.title("Configured pages respond and render a heading")
    @pytest.mark.regression
    def test_configured_pages_render(self, home_page: HomePage, environment: Environment) -> None:
        pages = DataReader.load("shared/urls.yaml")[environment.name]["pages"]
        for path in pages:
            with allure.step(f"Open {path}"):
                response = home_page.page.goto(home_page.url_for(path), wait_until="domcontentloaded")
                assert response is not None and response.status < 400, f"{path} -> {response and response.status}"
                home_page.cookie_banner.accept_if_present(1500)
                expect(home_page.page.get_by_role("heading").first).to_be_visible()
