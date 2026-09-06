"""Framework self-tests: browser + device configuration and safety guard."""

import allure
import pytest

from ui.utils.device_manager import DeviceManager, DeviceNotFoundError
from utils.common.runtime_context import RuntimeContext
from utils.config.environment_manager import Environment
from utils.security.safety_guard import SafetyLevel, is_allowed

pytestmark = [pytest.mark.framework, pytest.mark.read_only]


@allure.feature("Framework")
@allure.story("Browser & device configuration")
class TestDevices:
    def test_devices_yaml_lists_required_devices(self, device_manager: DeviceManager) -> None:
        for name in ("Pixel 5", "Pixel 7", "Galaxy S23", "iPhone 13", "iPhone 14", "iPhone 15"):
            assert name in device_manager.known_devices()

    def test_device_options_resolve(self, device_manager: DeviceManager, playwright) -> None:
        for name in device_manager.known_devices():
            options = device_manager.context_options(name, playwright)
            assert options["viewport"]["width"] > 0
            assert options.get("is_mobile") in (True, False)

    def test_unknown_device_error(self, device_manager: DeviceManager, playwright) -> None:
        with pytest.raises(DeviceNotFoundError):
            device_manager.context_options("Nokia 3310", playwright)

    def test_runtime_context_reflects_options(self, runtime_context: RuntimeContext) -> None:
        assert runtime_context.browser in {"chromium", "firefox", "webkit"}
        assert runtime_context.device_label == (runtime_context.device or "desktop")
        assert runtime_context.execution_dir


@allure.feature("Framework")
@allure.story("Safety guard")
class TestSafetyGuard:
    def test_prod_blocks_non_read_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ALLOW_PROD_WRITES", raising=False)
        prod = Environment("prod")
        assert is_allowed(SafetyLevel.READ_ONLY, prod)[0]
        for level in (SafetyLevel.DATA_CREATING, SafetyLevel.DATA_MODIFYING, SafetyLevel.DESTRUCTIVE):
            allowed, reason = is_allowed(level, prod)
            assert not allowed and "prod" in reason

    def test_local_allows_everything(self) -> None:
        local = Environment("local")
        assert all(is_allowed(level, local)[0] for level in SafetyLevel)

    def test_staging_blocks_destructive_only(self) -> None:
        staging = Environment("staging")
        assert is_allowed(SafetyLevel.DATA_MODIFYING, staging)[0]
        assert not is_allowed(SafetyLevel.DESTRUCTIVE, staging)[0]
