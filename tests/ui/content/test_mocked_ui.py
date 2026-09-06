"""
UI test with a MOCKED backend call (page.route).

Shows how to make a UI test deterministic when the API is unavailable.
Marked ``mocked`` so it is excluded from real integration runs.
"""

import allure
import pytest
from playwright.sync_api import expect

from api.mocks.ui_route_mocks import mock_failure, mock_json_response
from ui.pages.home_page import HomePage

pytestmark = [pytest.mark.ui, pytest.mark.mocked, pytest.mark.read_only]


@allure.feature("Mocking")
class TestMockedUi:
    @allure.title("page.route serves a mocked JSON payload to the browser")
    def test_mocked_api_in_browser(self, home_page: HomePage) -> None:
        mock_json_response(home_page.page, "**/api/content/pages", {"items": [{"id": "m", "title": "Mocked Drink"}]})
        home_page.open_and_prepare()
        payload = home_page.page.evaluate("() => fetch('/api/content/pages').then(r => r.json())")
        assert payload["items"][0]["title"] == "Mocked Drink"

    @allure.title("page.route can simulate a backend failure")
    def test_mocked_failure(self, home_page: HomePage) -> None:
        mock_failure(home_page.page, "**/api/content/pages", status=503)
        home_page.open_and_prepare()
        status = home_page.page.evaluate("() => fetch('/api/content/pages').then(r => r.status)")
        assert status == 503
        expect(home_page.headings.first).to_be_visible()  # page still usable
