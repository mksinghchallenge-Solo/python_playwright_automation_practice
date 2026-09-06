"""Optional broken-link check. Run with: pytest -m links"""

import allure
import pytest

from ui.pages.home_page import HomePage
from ui.utils.link_checker import LinkChecker
from utils.config.environment_manager import Environment

pytestmark = [pytest.mark.ui, pytest.mark.links, pytest.mark.read_only]


@allure.feature("Broken links")
class TestBrokenLinks:
    @allure.title("Home page internal links are not broken")
    def test_home_page_internal_links(self, prepared_home: HomePage, environment: Environment) -> None:
        checker = LinkChecker(environment.ui_base_url, check_external=False)
        results = checker.check(prepared_home.all_link_hrefs(), report_name="home_internal_links")
        broken = checker.broken(results)
        assert not broken, "Broken internal links:\n" + "\n".join(f"{r.status} {r.url} {r.error}" for r in broken)
