"""
API fixtures - clients, authentication and mock server.

Real-endpoint fixtures automatically ``pytest.skip`` when the environment
still contains ``<PLACEHOLDER>`` endpoints, so the suite stays green while
you discover and add the authorized APIs.
"""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest

from api.clients.auth_client import AuthClient, StaticTokenProvider, TokenManager
from api.clients.content_client import ContentClient
from api.clients.example_client import ExampleClient
from api.clients.profile_client import ProfileClient
from api.clients.user_client import UserClient
from api.mocks.mock_server import MockApiServer
from utils.config.environment_manager import Environment
from utils.data.test_data_factory import TestDataFactory, TestUser
from utils.logging.logger import get_logger

log = get_logger("ApiFixtures")


def require_real_api(environment: Environment, *endpoint_keys: str) -> None:
    """Skip the test when the real API / endpoints are not configured yet."""
    if not environment.api_is_configured():
        pytest.skip(
            f"Real API base URL not configured for env '{environment.name}' "
            f"(api.base_url is '{environment.api_base_url}'). Replace the placeholder in "
            f"{environment.file_path.name} once you have an authorized endpoint."
        )
    for key in endpoint_keys:
        if not environment.endpoint_is_configured(key):
            pytest.skip(
                f"Endpoint '{key}' is still a placeholder ({environment.endpoint(key)}) in "
                f"{environment.file_path.name}. See docs/api_discovery.md."
            )


# ------------------------------------------------------------ real clients
@pytest.fixture(scope="session")
def auth_client(environment: Environment) -> Generator[AuthClient, None, None]:
    require_real_api(environment, "login")
    client = AuthClient(environment)
    yield client
    client.close()


@pytest.fixture(scope="session")
def api_credentials() -> tuple[str, str]:
    """Credentials from .env (never hardcoded)."""
    email, password = os.getenv("API_USER_EMAIL", ""), os.getenv("API_USER_PASSWORD", "")
    if not email or not password:
        pytest.skip("API_USER_EMAIL / API_USER_PASSWORD not set in .env")
    return email, password


@pytest.fixture(scope="session")
def token_manager(auth_client: AuthClient, api_credentials: tuple[str, str]) -> TokenManager:
    """Session-wide token cache; refreshes automatically when expired."""
    email, password = api_credentials
    return TokenManager(auth_client, email, password)


@pytest.fixture(scope="session")
def profile_client(environment: Environment, token_manager: TokenManager) -> Generator[ProfileClient, None, None]:
    require_real_api(environment, "profile", "update_profile")
    client = ProfileClient(environment, auth_provider=token_manager)
    yield client
    client.close()


@pytest.fixture(scope="session")
def user_client(environment: Environment, token_manager: TokenManager) -> Generator[UserClient, None, None]:
    require_real_api(environment, "signup")
    client = UserClient(environment, auth_provider=token_manager)
    yield client
    client.close()


@pytest.fixture(scope="session")
def anonymous_user_client(environment: Environment) -> Generator[UserClient, None, None]:
    """User client WITHOUT auth - used for signup and negative tests."""
    require_real_api(environment, "signup")
    client = UserClient(environment)
    yield client
    client.close()


@pytest.fixture(scope="session")
def content_client(environment: Environment) -> Generator[ContentClient, None, None]:
    require_real_api(environment, "content")
    client = ContentClient(environment)
    yield client
    client.close()


@pytest.fixture
def invalid_token_profile_client(environment: Environment) -> Generator[ProfileClient, None, None]:
    """Profile client carrying a deliberately invalid token (negative tests)."""
    require_real_api(environment, "profile")
    client = ProfileClient(environment, auth_provider=StaticTokenProvider("invalid.token.value"))
    yield client
    client.close()


# ------------------------------------------------------- created test user
@pytest.fixture
def api_created_user(environment: Environment, anonymous_user_client: UserClient) -> Generator[TestUser, None, None]:
    """Create a unique user via API; delete it afterwards (API cleanup).

    DATA_CREATING - blocked on prod by the safety guard.
    """
    user = TestDataFactory.user("api")
    response = anonymous_user_client.create_user(
        {
            "email": user.email,
            "password": user.password,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "zip_code": user.zip_code,
        }
    )
    if response.status_code not in (200, 201):
        pytest.fail(f"Could not create test user via API: {response.describe()}\n{response.failure_report()}")
    user_id = str(response.json().get("id", ""))
    log.info("Created API test user %s (id=%s)", user.email, user_id)
    yield user

    # ---- cleanup with the user's own token
    try:
        auth = AuthClient(environment)
        manager = TokenManager(auth, user.email, user.password)
        cleanup_client = UserClient(environment, auth_provider=manager)
        delete = cleanup_client.delete_user(user_id)
        log.info("Cleanup delete user %s -> %s", user.email, delete.status_code)
    except Exception as exc:  # cleanup problems are logged, never hidden
        log.error("Cleanup failed for %s: %s", user.email, exc)


# ---------------------------------------------------------- example client
@pytest.fixture(scope="session")
def example_client(environment: Environment) -> Generator[ExampleClient, None, None]:
    """Client for the safe public echo API (httpbin) - framework validation only."""
    client = ExampleClient(environment)
    yield client
    client.close()


# ------------------------------------------------------------ mock server
@pytest.fixture
def mock_server() -> Generator[MockApiServer, None, None]:
    """Local mock API on a free port - for tests marked ``mocked``."""
    server = MockApiServer().start()
    yield server
    server.stop()
