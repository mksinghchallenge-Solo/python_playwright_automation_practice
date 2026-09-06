"""Optional accessibility scans (axe-core). Run with: pytest -m accessibility"""

import allure
import pytest

from ui.pages.home_page import HomePage
from ui.pages.login_page import LoginPage
from ui.utils.accessibility import AccessibilityChecker
from utils.common.runtime_context import RuntimeContext

pytestmark = [pytest.mark.ui, pytest.mark.accessibility, pytest.mark.read_only]


@allure.feature("Accessibility")
class TestAccessibility:
    @allure.title("Home page has no critical/serious WCAG AA violations")
    def test_home_page_wcag_aa(self, prepared_home: HomePage, runtime_context: RuntimeContext) -> None:
        result = AccessibilityChecker(prepared_home.page, runtime_context).run(level="AA")
        severe = result.violations_by_impact()
        assert not severe, result.summary()

    @allure.title("Login page has no WCAG A violations")
    def test_login_page_wcag_a(self, login_page: LoginPage, runtime_context: RuntimeContext) -> None:
        login_page.open_and_prepare()
        result = AccessibilityChecker(login_page.page, runtime_context).run(level="A")
        assert result.violation_count == 0, result.summary()
