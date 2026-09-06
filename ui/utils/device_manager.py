"""
Device manager - resolves ``--device`` names into Playwright context options.

Reads ``config/devices/devices.yaml``. Devices that exist in Playwright's
built-in registry are taken from there; custom devices use the explicit
descriptor from the YAML file.

NOTE: this is *browser emulation* (viewport, UA, touch, scale factor), not a
physical Android/iPhone device.
"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Playwright

from utils.common.file_utils import read_yaml
from utils.config.config_reader import CONFIG_DIR
from utils.logging.logger import get_logger

DEVICES_FILE = CONFIG_DIR / "devices" / "devices.yaml"
log = get_logger("DeviceManager")


class DeviceNotFoundError(Exception):
    """Raised when a device is not in devices.yaml nor in Playwright's registry."""


class DeviceManager:
    """Resolve device names to ``browser.new_context(**options)`` kwargs."""

    def __init__(self) -> None:
        data = read_yaml(DEVICES_FILE) or {}
        self.devices: dict[str, dict[str, Any]] = data.get("devices", {}) or {}

    def known_devices(self) -> list[str]:
        return sorted(self.devices)

    def engine_for(self, device_name: str) -> str:
        """Which Playwright engine emulates this device best (chromium / webkit)."""
        entry = self.devices.get(device_name, {})
        return str(entry.get("engine", "chromium"))

    def context_options(self, device_name: str, playwright: Playwright) -> dict[str, Any]:
        entry = self.devices.get(device_name)
        if entry is None:
            # Allow any Playwright built-in device even if not listed in YAML.
            if device_name in playwright.devices:
                log.info("Device '%s' resolved from Playwright registry (not in devices.yaml)", device_name)
                return dict(playwright.devices[device_name])
            raise DeviceNotFoundError(
                f"Unknown device '{device_name}'. Known: {self.known_devices()} "
                f"or any Playwright built-in device name."
            )
        if "descriptor" in entry:
            descriptor = dict(entry["descriptor"])
            log.info("Device '%s' resolved from custom descriptor", device_name)
            return descriptor
        registry_name = str(entry.get("playwright_name", device_name))
        if registry_name not in playwright.devices:
            raise DeviceNotFoundError(
                f"Device '{device_name}' maps to Playwright device '{registry_name}' which does not exist "
                f"in this Playwright version."
            )
        options = dict(playwright.devices[registry_name])
        log.info("Device '%s' resolved from Playwright registry as '%s'", device_name, registry_name)
        return options
