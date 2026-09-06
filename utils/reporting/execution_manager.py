"""
Execution manager.

Creates ONE unique directory per test run::

    reports/
    └── 2026-09-06/
        └── execution_02-35-41/
            ├── allure-results/
            ├── allure-report/
            ├── junit/
            ├── api/{requests,responses,logs}/
            ├── ui/{screenshots,videos,traces,logs}/
            ├── e2e/
            ├── framework/
            ├── execution.json
            └── execution_summary.html

Parallel safety (pytest-xdist)
------------------------------
The xdist *controller* creates the directory first and publishes its path in
the ``EXECUTION_DIR`` environment variable. Worker processes inherit that
variable and reuse the same directory, so all workers write into one
execution folder while file names stay unique (worker id + timestamp).
If a second execution is started in the same second, a numeric suffix is
appended - previous executions are NEVER overwritten.
"""

from __future__ import annotations

import json
import os
import socket
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.config.config_reader import PROJECT_ROOT

REPORTS_ROOT = PROJECT_ROOT / "reports"
EXECUTION_DIR_ENV = "EXECUTION_DIR"

SUBDIRECTORIES: tuple[str, ...] = (
    "allure-results",
    "allure-report",
    "junit",
    "api/requests",
    "api/responses",
    "api/logs",
    "ui/screenshots",
    "ui/videos",
    "ui/traces",
    "ui/logs",
    "e2e",
    "framework",
    "logs",
)


class ExecutionManager:
    """Owns the unique execution directory and run-level metadata."""

    def __init__(self, reports_root: Path = REPORTS_ROOT) -> None:
        self.reports_root = reports_root
        self.started_at = datetime.now()
        self.execution_dir: Path = self._resolve_execution_dir()
        self.execution_id: str = f"{self.execution_dir.parent.name}_{self.execution_dir.name}"
        self._create_subdirectories()

    # ----------------------------------------------------------- directory
    def _resolve_execution_dir(self) -> Path:
        """Reuse the controller's directory on xdist workers, else create one."""
        existing = os.getenv(EXECUTION_DIR_ENV)
        if existing:
            return Path(existing)

        day_dir = self.reports_root / self.started_at.strftime("%Y-%m-%d")
        base_name = f"execution_{self.started_at.strftime('%H-%M-%S')}"
        candidate = day_dir / base_name
        suffix = 1
        while candidate.exists():  # never overwrite a previous execution
            candidate = day_dir / f"{base_name}_{suffix}"
            suffix += 1
        candidate.mkdir(parents=True, exist_ok=False)
        os.environ[EXECUTION_DIR_ENV] = str(candidate)
        return candidate

    def _create_subdirectories(self) -> None:
        for sub in SUBDIRECTORIES:
            (self.execution_dir / sub).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------- helpers
    @property
    def worker_id(self) -> str:
        return os.getenv("PYTEST_XDIST_WORKER", "main")

    @property
    def is_controller(self) -> bool:
        """True in the main process (or in a non-xdist run)."""
        return "PYTEST_XDIST_WORKER" not in os.environ

    def path(self, *parts: str) -> Path:
        """Return ``execution_dir / parts...`` creating parent directories."""
        target = self.execution_dir.joinpath(*parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    @property
    def allure_results_dir(self) -> Path:
        return self.execution_dir / "allure-results"

    @property
    def allure_report_dir(self) -> Path:
        return self.execution_dir / "allure-report"

    @property
    def junit_file(self) -> Path:
        return self.execution_dir / "junit" / "junit.xml"

    @property
    def summary_file(self) -> Path:
        return self.execution_dir / "execution_summary.html"

    @property
    def metadata_file(self) -> Path:
        return self.execution_dir / "execution.json"

    def log_file(self, layer: str = "framework") -> Path:
        """Per-worker log file so parallel workers never interleave writes."""
        folder = "logs" if layer == "framework" else f"{layer}/logs"
        return self.path(folder, f"{self.worker_id}.log")

    # ------------------------------------------------------------ metadata
    def write_metadata(self, **extra: Any) -> Path:
        """Persist run metadata (merged with anything already written)."""
        data: dict[str, Any] = {}
        if self.metadata_file.exists():
            try:
                data = json.loads(self.metadata_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
        data.update(
            {
                "execution_id": self.execution_id,
                "execution_dir": str(self.execution_dir),
                "started_at": data.get("started_at", self.started_at.isoformat(timespec="seconds")),
                "host": socket.gethostname(),
            }
        )
        data.update(extra)
        self.metadata_file.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return self.metadata_file

    def read_metadata(self) -> dict[str, Any]:
        if not self.metadata_file.exists():
            return {}
        return json.loads(self.metadata_file.read_text(encoding="utf-8"))


_execution_singleton: ExecutionManager | None = None


def get_execution_manager() -> ExecutionManager:
    """Return the process-wide :class:`ExecutionManager`."""
    global _execution_singleton
    if _execution_singleton is None:
        _execution_singleton = ExecutionManager()
    return _execution_singleton


def list_executions(reports_root: Path = REPORTS_ROOT) -> list[Path]:
    """Return every execution directory, oldest first (used by cleanup + history)."""
    if not reports_root.exists():
        return []
    executions = [
        exec_dir
        for day_dir in reports_root.iterdir()
        if day_dir.is_dir()
        for exec_dir in day_dir.iterdir()
        if exec_dir.is_dir() and exec_dir.name.startswith("execution_")
    ]
    return sorted(executions, key=lambda p: p.stat().st_mtime)
