"""
Root conftest - wires the framework into pytest.

Responsibilities (in execution order):

1. Register CLI options (``--env``, ``--device``, ``--screenshot-mode``...)
   and translate ``--browser=chrome|msedge`` into Playwright channels.
2. Create the unique execution directory and point Allure / JUnit at it.
3. Configure logging (console + per-worker file) with secret masking.
4. Enforce the safety guard before each test.
5. Expose test outcome to fixtures (``item.rep_call``).
6. Write ``execution.json`` + ``execution_summary.html`` at session end.

Fixtures themselves live in ``fixtures/`` and are loaded via ``pytest_plugins``.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.config.config_reader import get_config  # noqa: E402
from utils.config.environment_manager import get_environment, resolve_environment_name  # noqa: E402
from utils.logging.logger import attach_file_handler, configure_logging, get_logger  # noqa: E402
from utils.reporting.allure_manager import write_environment_properties, write_executor_json  # noqa: E402
from utils.reporting.execution_manager import get_execution_manager  # noqa: E402
from utils.security.safety_guard import check_test_allowed  # noqa: E402

pytest_plugins = [
    "fixtures.shared_fixtures",
    "fixtures.api_fixtures",
    "fixtures.ui_fixtures",
    "fixtures.e2e_fixtures",
]

log = get_logger("conftest")

BRANDED_BROWSERS = {"chrome": ("chromium", "chrome"), "msedge": ("chromium", "msedge"), "edge": ("chromium", "msedge")}


# ------------------------------------------------------------ CLI options
def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("coca-cola-automation")
    group.addoption("--env", action="store", default=None, help="Environment: local | qa | staging | prod")
    group.addoption(
        "--screenshot-mode",
        action="store",
        default=None,
        choices=["always", "retain-on-failure", "never"],
        help="Screenshot policy",
    )
    group.addoption(
        "--video-mode",
        action="store",
        default=None,
        choices=["always", "retain-on-failure", "never"],
        help="Video policy",
    )
    group.addoption(
        "--trace-mode",
        action="store",
        default=None,
        choices=["always", "retain-on-failure", "never"],
        help="Trace policy",
    )
    group.addoption(
        "--mocked-only",
        action="store_true",
        default=False,
        help="Run only tests marked 'mocked' (never hits real APIs)",
    )


def _translate_branded_browser(argv: list[str]) -> str | None:
    """Turn ``--browser=chrome`` / ``--browser msedge`` into chromium + channel.

    pytest-playwright only accepts chromium/firefox/webkit for ``--browser``,
    so we rewrite the argument before it validates it.
    """
    channel: str | None = None
    for index, arg in enumerate(argv):
        value: str | None = None
        if arg.startswith("--browser="):
            value = arg.split("=", 1)[1]
        elif arg == "--browser" and index + 1 < len(argv):
            value = argv[index + 1]
        if value and value.lower() in BRANDED_BROWSERS:
            engine, channel = BRANDED_BROWSERS[value.lower()]
            if arg.startswith("--browser="):
                argv[index] = f"--browser={engine}"
            else:
                argv[index + 1] = engine
    return channel


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config: pytest.Config, parser: pytest.Parser, args: list[str]) -> None:
    channel = _translate_branded_browser(args)
    if channel:
        os.environ["COCACOLA_BROWSER_CHANNEL"] = channel
    # Default browser from config when none given on the CLI.
    if not any(a.startswith("--browser") for a in args):
        configured = get_config().browser_name
        if configured in BRANDED_BROWSERS:
            engine, channel = BRANDED_BROWSERS[configured]
            os.environ["COCACOLA_BROWSER_CHANNEL"] = channel
            args.append(f"--browser={engine}")
        elif configured in ("chromium", "firefox", "webkit"):
            args.append(f"--browser={configured}")


# --------------------------------------------------------------- configure
def pytest_configure(config: pytest.Config) -> None:
    # 1. environment selection (CLI > ENV > config.yaml)
    env_name = resolve_environment_name(config.getoption("--env"))
    os.environ["ENV"] = env_name
    environment = get_environment(env_name, reload=True)
    configure_logging()

    # Collection-only runs (pytest --co) must not create execution folders.
    if config.getoption("--collect-only", default=False) or config.getoption("--help", default=False):
        return

    # 2. execution directory + reporting paths
    execution = get_execution_manager()
    if config.option.allure_report_dir is None and get_config().get("reporting.allure", True):
        config.option.allure_report_dir = str(execution.allure_results_dir)
    if not config.option.xmlpath and get_config().get("reporting.junit", True):
        config.option.xmlpath = str(execution.junit_file)
    # Keep pytest-playwright's own output dir inside the execution folder too.
    if getattr(config.option, "output", None) in (None, "test-results"):
        config.option.output = str(execution.execution_dir / "ui" / "playwright-output")

    # 3. logging
    attach_file_handler(execution.log_file("framework"), name="execution")
    config._cocacola_channel = os.getenv("COCACOLA_BROWSER_CHANNEL")  # type: ignore[attr-defined]
    config._cocacola_started = time.time()  # type: ignore[attr-defined]

    if execution.is_controller:
        log.info("=" * 78)
        log.info("Execution %s | env=%s | dir=%s", execution.execution_id, environment.name, execution.execution_dir)
        log.info("=" * 78)
        write_environment_properties(
            execution.allure_results_dir,
            {
                "Environment": environment.name,
                "UI.Base.URL": environment.ui_base_url,
                "API.Base.URL": environment.api_base_url,
                "Browser": (config.option.browser or [get_config().browser_name])[0],
                "Browser.Channel": os.getenv("COCACOLA_BROWSER_CHANNEL") or "-",
                "Device": config.getoption("--device") or "desktop",
                "Execution.ID": execution.execution_id,
                "Python": sys.version.split()[0],
            },
        )
        write_executor_json(
            execution.allure_results_dir,
            execution.execution_id,
            os.getenv("BUILD_URL") or os.getenv("CI_JOB_URL") or "",
        )
        execution.write_metadata(
            environment=environment.name,
            browser=(config.option.browser or [get_config().browser_name])[0],
            channel=os.getenv("COCACOLA_BROWSER_CHANNEL"),
            device=config.getoption("--device") or "desktop",
            headless=not config.getoption("--headed"),
            workers=getattr(config.option, "numprocesses", None) or 1,
            reruns=getattr(config.option, "reruns", 0) or 0,
            command=" ".join(sys.argv),
        )


# ------------------------------------------------------- collection hooks
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-add layer markers from the path + honour --mocked-only."""
    mocked_only = config.getoption("--mocked-only")
    selected, deselected = [], []
    for item in items:
        path = str(item.fspath).replace("\\", "/")
        for layer in ("api", "ui", "e2e", "framework"):
            if f"/tests/{layer}/" in path:
                item.add_marker(getattr(pytest.mark, layer))
        if mocked_only and not item.get_closest_marker("mocked"):
            deselected.append(item)
        else:
            selected.append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


# --------------------------------------------------------- per-test hooks
@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Safety guard: block risky tests in protected environments."""
    check_test_allowed(item, get_environment())


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]) -> Generator[None, Any, None]:
    """Expose setup/call/teardown reports on the item for fixtures."""
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)
    if report.when == "call" and report.failed:
        log.error("TEST FAILED | %s | %s", item.nodeid, _short_error(report))


def _short_error(report: pytest.TestReport) -> str:
    text = report.longreprtext if hasattr(report, "longreprtext") else str(report.longrepr)
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return lines[-1][:300] if lines else "unknown error"


# --------------------------------------------------------- session finish
def _execution_started(config: pytest.Config) -> bool:
    return hasattr(config, "_cocacola_started")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not _execution_started(session.config):
        return
    execution = get_execution_manager()
    if not execution.is_controller:
        return
    duration = time.time() - getattr(session.config, "_cocacola_started", time.time())
    try:
        from utils.reporting.summary_builder import build_execution_summary

        summary_path = build_execution_summary(execution, duration_seconds=duration, exit_status=int(exitstatus))
        log.info("Execution summary: %s", summary_path)
    except Exception as exc:  # summary must never break the run
        log.error("Could not build execution summary: %s", exc)
    log.info("Allure results: %s", execution.allure_results_dir)
    log.info("JUnit XML     : %s", execution.junit_file)
    log.info(
        "Generate report: allure generate %s -o %s --clean", execution.allure_results_dir, execution.allure_report_dir
    )


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: pytest.Config) -> None:
    if not _execution_started(config):
        return
    execution = get_execution_manager()
    if execution.is_controller:
        terminalreporter.write_sep("=", "Coca-Cola Automation - execution artifacts")
        terminalreporter.write_line(f"Execution dir : {execution.execution_dir}")
        terminalreporter.write_line(f"Summary       : {execution.summary_file}")
        terminalreporter.write_line(f"Allure results: {execution.allure_results_dir}")
        terminalreporter.write_line(f"JUnit XML     : {execution.junit_file}")
