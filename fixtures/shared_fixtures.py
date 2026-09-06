"""
Shared fixtures used by API, UI and E2E tests.

Loaded automatically through ``pytest_plugins`` in the root ``conftest.py``.
"""

from __future__ import annotations

import logging
from collections.abc import Generator

import pytest

from utils.artifacts.artifact_manager import ArtifactManager, get_artifact_manager, safe_name
from utils.common.runtime_context import RuntimeContext
from utils.config.config_reader import ConfigReader, get_config
from utils.config.environment_manager import Environment, get_environment
from utils.data.data_reader import DataReader
from utils.data.test_data_factory import TestDataFactory, TestUser
from utils.logging.logger import ROOT_LOGGER_NAME, clear_log_context, get_logger, set_log_context
from utils.logging.masking import mask_text
from utils.reporting.allure_manager import add_labels, attach_text
from utils.reporting.execution_manager import ExecutionManager, get_execution_manager

log = get_logger("Fixtures")


# ----------------------------------------------------------------- config
@pytest.fixture(scope="session")
def config() -> ConfigReader:
    """Main configuration (config/config.yaml + env overrides)."""
    return get_config()


@pytest.fixture(scope="session")
def environment() -> Environment:
    """Active environment (config/environments/<env>.yaml)."""
    return get_environment()


@pytest.fixture(scope="session")
def execution() -> ExecutionManager:
    """Unique execution directory for this run."""
    return get_execution_manager()


@pytest.fixture(scope="session")
def artifacts() -> ArtifactManager:
    return get_artifact_manager()


@pytest.fixture(scope="session")
def runtime_context(
    pytestconfig: pytest.Config, config: ConfigReader, environment: Environment, execution: ExecutionManager
) -> RuntimeContext:
    """Describes how this run is configured (browser/device/env/artifact policy)."""
    return RuntimeContext(
        environment=environment.name,
        browser=(pytestconfig.option.browser or [config.browser_name])[0],
        channel=pytestconfig.getoption("--browser-channel") or getattr(pytestconfig, "_cocacola_channel", None),
        headless=not pytestconfig.getoption("--headed") and config.headless,
        slow_mo=int(pytestconfig.getoption("--slowmo") or config.slow_mo),
        device=pytestconfig.getoption("--device") or (config.mobile_device if config.mobile_enabled else None),
        screenshot_mode=pytestconfig.getoption("--screenshot-mode") or config.screenshot_mode,
        video_mode=pytestconfig.getoption("--video-mode") or config.video_mode,
        trace_mode=pytestconfig.getoption("--trace-mode") or config.trace_mode,
        ui_base_url=environment.ui_base_url,
        api_base_url=environment.api_base_url,
        worker_id=execution.worker_id,
        execution_id=execution.execution_id,
        execution_dir=str(execution.execution_dir),
    )


# ------------------------------------------------------------------- data
@pytest.fixture(scope="session")
def data_reader() -> type[DataReader]:
    return DataReader


@pytest.fixture(scope="session")
def data_factory() -> type[TestDataFactory]:
    return TestDataFactory


@pytest.fixture
def generated_user(data_factory: type[TestDataFactory]) -> TestUser:
    """A brand-new unique user object (not yet created anywhere)."""
    user = data_factory.user()
    log.info("Generated test user %s", user.email)
    return user


# --------------------------------------------------------- per-test setup
class _MemoryLogHandler(logging.Handler):
    """Collects log lines for one test so they can be attached to Allure."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []
        self.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)-24s | %(message)s", "%Y-%m-%d %H:%M:%S")
        )

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(mask_text(self.format(record)))


def _layer_of(nodeid: str) -> str:
    for layer in ("api", "ui", "e2e", "framework"):
        if nodeid.startswith(f"tests/{layer}/") or f"/tests/{layer}/" in nodeid:
            return layer
    return "framework"


@pytest.fixture(autouse=True)
def _test_context(
    request: pytest.FixtureRequest, runtime_context: RuntimeContext, execution: ExecutionManager
) -> Generator[None, None, None]:
    """Autouse: log context, Allure labels and per-test log attachment."""
    item = request.node
    layer = _layer_of(item.nodeid)
    browser = request.getfixturevalue("browser_name") if "browser_name" in item.fixturenames else "-"
    set_log_context(
        test=item.name, browser=browser, device=runtime_context.device_label, environment=runtime_context.environment
    )
    add_labels(
        layer=layer,
        environment=runtime_context.environment,
        browser=browser,
        device=runtime_context.device_label,
        worker=execution.worker_id,
    )
    for marker in ("smoke", "regression", "read_only", "data_creating", "data_modifying", "destructive"):
        if item.get_closest_marker(marker):
            add_labels(tag=marker)

    handler = _MemoryLogHandler()
    logging.getLogger(ROOT_LOGGER_NAME).addHandler(handler)
    log.info("==== TEST START | %s | layer=%s ====", item.nodeid, layer)
    try:
        yield
    finally:
        outcome = "PASSED"
        rep_call = getattr(item, "rep_call", None)
        rep_setup = getattr(item, "rep_setup", None)
        if rep_setup is not None and rep_setup.failed:
            outcome = "ERROR"
        elif rep_call is not None:
            outcome = "PASSED" if rep_call.passed else ("SKIPPED" if rep_call.skipped else "FAILED")
        log.info("==== TEST END   | %s | %s ====", item.name, outcome)
        logging.getLogger(ROOT_LOGGER_NAME).removeHandler(handler)
        text = "\n".join(handler.lines)
        attach_text("test.log", text, mask=False)
        try:
            log_dir = "logs" if layer == "framework" else f"{layer}/logs"
            # item.name is the raw pytest id; parameterized ids can contain characters
            # that are illegal on NTFS (":  <  >  |  *  ?) and rejected by actions/upload-artifact,
            # so always persist artifacts under a filesystem-safe name.
            execution.path(log_dir, f"{safe_name(item.name)}__{execution.worker_id}.log").write_text(
                text, encoding="utf-8"
            )
        except OSError as exc:
            log.error("Could not write per-test log: %s", exc)
        clear_log_context()
