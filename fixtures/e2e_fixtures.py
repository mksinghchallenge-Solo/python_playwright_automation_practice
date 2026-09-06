"""
E2E fixtures - helpers that combine the API and UI layers.

Rules enforced here (see docs/e2e_automation.md):

* API tokens and browser sessions are NOT assumed to be interchangeable.
  The UI logs in through the UI; the API authenticates through the API.
* Setup prefers the API (fast, reliable); verification uses whichever layer
  the business flow demands; cleanup prefers the API.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from api.clients.auth_client import AuthClient, TokenManager
from api.clients.profile_client import ProfileClient
from ui.pages.login_page import LoginPage
from ui.pages.profile_page import ProfilePage
from utils.config.environment_manager import Environment
from utils.data.test_data_factory import TestUser
from utils.logging.logger import get_logger
from utils.reporting.allure_manager import step

log = get_logger("E2eFixtures")


@dataclass
class E2eActors:
    """Bundle of the API client + UI pages acting for one user."""

    user: TestUser
    profile_api: ProfileClient
    login_page: LoginPage
    profile_page: ProfilePage

    def ui_login(self) -> None:
        with step(f"UI login as {self.user.email}"):
            self.login_page.open_and_prepare()
            self.login_page.login_as(self.user)
            self.profile_page.expect_loaded()


@pytest.fixture
def e2e_actors(
    environment: Environment, api_created_user: TestUser, login_page: LoginPage, profile_page: ProfilePage
) -> E2eActors:
    """User created via API + authenticated API client + UI pages for that user."""
    auth = AuthClient(environment)
    manager = TokenManager(auth, api_created_user.email, api_created_user.password)
    profile_api = ProfileClient(environment, auth_provider=manager)
    log.info("E2E actors ready for %s", api_created_user.email)
    return E2eActors(api_created_user, profile_api, login_page, profile_page)
