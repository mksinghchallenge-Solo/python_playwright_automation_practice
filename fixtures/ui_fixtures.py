"""
UI fixtures - browser, context, page and Page Object factories.

We build on top of ``pytest-playwright`` (its ``playwright`` / ``browser_name``
/ ``browser_type_launch_args`` fixtures) but own the *context* so that:

* device emulation comes from ``config/devices/devices.yaml`` (``--device``)
* branded channels work (``--browser=chrome`` / ``--browser=msedge``)
* videos / traces / screenshots follow the framework policy
  (always | retain-on-failure | never) and land in the unique execution
  folder with meaningful names
* every artifact is attached to Allure
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright

from ui.pages.edit_profile_page import EditProfilePage
from ui.pages.home_page import HomePage
from ui.pages.login_page import LoginPage
from ui.pages.profile_page import ProfilePage
from ui.pages.signup_page import SignupPage
from ui.utils.device_manager import DeviceManager
from utils.artifacts.artifact_manager import ArtifactManager
from utils.common.runtime_context import RuntimeContext
from utils.config.config_reader import ConfigReader
from utils.logging.logger import get_logger
from utils.reporting.allure_manager import attach_file, attach_text

log = get_logger("UiFixtures")

BRANDED_CHANNELS = {"chrome": "chrome", "msedge": "msedge", "edge": "msedge", "chrome-beta": "chrome-beta"}


# --------------------------------------------------------------- browser
@pytest.fixture(scope="session")
def device_manager() -> DeviceManager:
    return DeviceManager()


@pytest.fixture(scope="session")
def browser_type_launch_args(
    pytestconfig: pytest.Config, config: ConfigReader, runtime_context: RuntimeContext
) -> dict[str, Any]:
    """Launch options merged from config + CLI (headed/slowmo/channel)."""
    launch: dict[str, Any] = {
        "headless": runtime_context.headless,
        "slow_mo": runtime_context.slow_mo,
    }
    if runtime_context.channel:
        launch["channel"] = runtime_context.channel

    # Optional: point Playwright at a specific Chromium binary (e.g. restricted
    # CI images). Leave PLAYWRIGHT_CHROMIUM_EXECUTABLE unset in normal use.
    custom_executable = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if custom_executable and runtime_context.browser == "chromium" and not runtime_context.channel:
        launch["executable_path"] = custom_executable
        launch["args"] = ["--no-sandbox", "--disable-dev-shm-usage", "--no-zygote", "--disable-gpu"]
        log.info("Using custom Chromium executable: %s", custom_executable)
    log.info("Browser launch args: %s", launch)
    return launch


@pytest.fixture(scope="session")
def browser_context_args(
    playwright: Playwright,
    config: ConfigReader,
    runtime_context: RuntimeContext,
    device_manager: DeviceManager,
    artifacts: ArtifactManager,
) -> dict[str, Any]:
    """Context options: viewport/locale + device emulation + video policy."""
    args: dict[str, Any] = {
        "locale": config.get("browser.locale", "en-US"),
        "timezone_id": config.get("browser.timezone", "America/New_York"),
        "ignore_https_errors": bool(config.get("browser.ignore_https_errors", False)),
        "base_url": runtime_context.ui_base_url,
        "viewport": config.viewport,
    }
    if runtime_context.device:
        device_options = device_manager.context_options(runtime_context.device, playwright)
        # Playwright's descriptor uses default_browser_type; new_context doesn't accept it.
        device_options.pop("default_browser_type", None)
        args.update(device_options)
        runtime_context.device_descriptor = device_options
        log.info(
            "Mobile emulation enabled: %s -> %s",
            runtime_context.device,
            {k: device_options.get(k) for k in ("viewport", "is_mobile", "has_touch")},
        )
    if runtime_context.video_mode in ("always", "retain-on-failure"):
        args["record_video_dir"] = str(artifacts.video_dir())
        args["record_video_size"] = config.get("artifacts.video_size", {"width": 1280, "height": 720})
    return args


@pytest.fixture
def context(
    browser: Browser, browser_context_args: dict[str, Any], config: ConfigReader, runtime_context: RuntimeContext
) -> Generator[BrowserContext, None, None]:
    """A fresh isolated browser context per test with tracing per policy."""
    context = browser.new_context(**browser_context_args)
    context.set_default_timeout(config.action_timeout_ms)
    context.set_default_navigation_timeout(config.page_load_timeout_ms)
    if runtime_context.trace_mode in ("always", "retain-on-failure"):
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
    yield context
    context.close()


@pytest.fixture
def page(
    context: BrowserContext,
    request: pytest.FixtureRequest,
    runtime_context: RuntimeContext,
    artifacts: ArtifactManager,
    config: ConfigReader,
) -> Generator[Page, None, None]:
    """The page used by a test. Handles screenshot/video/trace on teardown."""
    page = context.new_page()
    from playwright.sync_api import expect

    expect.set_options(timeout=config.expect_timeout_ms)
    yield page

    failed = _test_failed(request)
    test_name = request.node.name
    browser_label, device_label = runtime_context.browser_label, runtime_context.device_label

    # ---- screenshot
    if runtime_context.screenshot_mode == "always" or (
        runtime_context.screenshot_mode == "retain-on-failure" and failed
    ):
        suffix = "failure" if failed else "success"
        path = artifacts.screenshot_path(test_name, browser_label, device_label, suffix)
        try:
            if not page.is_closed():
                page.screenshot(path=str(path), full_page=bool(config.get("artifacts.screenshot_full_page", True)))
                attach_file(path, name=f"screenshot-{suffix}")
                log.info("Screenshot saved: %s", path)
        except Exception as exc:
            log.error("Screenshot capture failed for %s: %s", test_name, exc)

    # ---- trace
    if runtime_context.trace_mode in ("always", "retain-on-failure"):
        keep = runtime_context.trace_mode == "always" or failed
        trace_path = artifacts.trace_path(test_name, browser_label, device_label)
        try:
            if keep:
                context.tracing.stop(path=str(trace_path))
                attach_file(trace_path, name="playwright-trace.zip")
                attach_text("trace-hint", f"Open with: playwright show-trace {trace_path}", mask=False)
                log.info("Trace saved: %s", trace_path)
            else:
                context.tracing.stop()
        except Exception as exc:
            log.error("Trace handling failed for %s: %s", test_name, exc)

    # ---- video (file is only final after page/context close)
    video = page.video if runtime_context.video_mode in ("always", "retain-on-failure") else None
    if not page.is_closed():
        page.close()
    if video is not None:
        keep = runtime_context.video_mode == "always" or failed
        try:
            raw_path = Path(video.path())
            if keep:
                final_path = artifacts.video_path(test_name, browser_label, device_label)
                context.close()  # flush video file
                if raw_path.exists():
                    shutil.move(str(raw_path), str(final_path))
                    attach_file(final_path, name="video")
                    log.info("Video saved: %s", final_path)
            else:
                context.close()
                if raw_path.exists():
                    raw_path.unlink()
        except Exception as exc:
            log.error("Video handling failed for %s: %s", test_name, exc)


def _test_failed(request: pytest.FixtureRequest) -> bool:
    rep_call = getattr(request.node, "rep_call", None)
    rep_setup = getattr(request.node, "rep_setup", None)
    return bool((rep_call is not None and rep_call.failed) or (rep_setup is not None and rep_setup.failed))


# ------------------------------------------------------- page object factories
@pytest.fixture
def home_page(page: Page, runtime_context: RuntimeContext) -> HomePage:
    return HomePage(page, runtime_context)


@pytest.fixture
def login_page(page: Page, runtime_context: RuntimeContext) -> LoginPage:
    return LoginPage(page, runtime_context)


@pytest.fixture
def signup_page(page: Page, runtime_context: RuntimeContext) -> SignupPage:
    return SignupPage(page, runtime_context)


@pytest.fixture
def profile_page(page: Page, runtime_context: RuntimeContext) -> ProfilePage:
    return ProfilePage(page, runtime_context)


@pytest.fixture
def edit_profile_page(page: Page, runtime_context: RuntimeContext) -> EditProfilePage:
    return EditProfilePage(page, runtime_context)


@pytest.fixture
def prepared_home(home_page: HomePage) -> HomePage:
    """Home page already opened with cookies accepted and popups dismissed."""
    return home_page.open_and_prepare()
