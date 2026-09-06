"""Framework self-tests: configuration + environment selection."""

import os

import allure
import pytest

from utils.config.config_reader import ConfigReader, get_config
from utils.config.environment_manager import Environment, EnvironmentConfigError, get_environment

pytestmark = [pytest.mark.framework, pytest.mark.read_only]


@allure.feature("Framework")
@allure.story("Configuration")
class TestConfiguration:
    @allure.severity(allure.severity_level.CRITICAL)
    def test_main_config_loads(self, config: ConfigReader) -> None:
        assert config.browser_name in {"chromium", "chrome", "msedge", "firefox", "webkit"}
        assert isinstance(config.headless, bool)
        assert config.get("timeouts.page_load_ms") > 0

    def test_dotted_get_with_default(self, config: ConfigReader) -> None:
        assert config.get("does.not.exist", "fallback") == "fallback"

    def test_artifact_policies_are_valid(self, config: ConfigReader) -> None:
        for mode in (config.screenshot_mode, config.video_mode, config.trace_mode):
            assert mode in {"always", "retain-on-failure", "never"}

    def test_env_override_changes_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HEADLESS", "false")
        monkeypatch.setenv("RETRIES", "3")
        fresh = ConfigReader()
        assert fresh.headless is False
        assert fresh.get("execution.retries") == 3


@allure.feature("Framework")
@allure.story("Environment selection")
class TestEnvironment:
    @pytest.mark.parametrize("name", ["local", "qa", "staging", "prod"])
    def test_each_environment_file_loads(self, name: str) -> None:
        env = Environment(name)
        assert env.name == name
        assert env.ui_base_url.startswith("http")
        assert isinstance(env.allows("read_only"), bool)

    def test_unknown_environment_rejected(self) -> None:
        with pytest.raises(EnvironmentConfigError):
            Environment("moon")

    def test_active_environment_matches_env_variable(self, environment: Environment) -> None:
        assert environment.name == os.environ["ENV"]

    def test_placeholder_detection(self) -> None:
        qa = Environment("qa")
        assert qa.is_placeholder("<AUTH_ENDPOINT>")
        assert not qa.is_placeholder("/api/v1/login")
        assert qa.api_is_configured() is False or not qa.is_placeholder(qa.api_base_url)

    def test_prod_blocks_writes_by_default(self) -> None:
        prod = Environment("prod")
        assert prod.allows("read_only") is True
        assert prod.allows("data_creating") is False
        assert prod.allows("destructive") is False

    def test_url_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UI_BASE_URL", "https://override.example.com/")
        env = Environment("qa")
        assert env.ui_base_url == "https://override.example.com"

    def test_get_environment_singleton(self, environment: Environment) -> None:
        assert get_environment() is environment
        assert get_config() is get_config()
