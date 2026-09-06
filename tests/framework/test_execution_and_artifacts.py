"""Framework self-tests: execution directories + artifact manager."""

import json
import os
import re
from pathlib import Path

import allure
import pytest

from utils.artifacts.artifact_manager import ArtifactManager, safe_name
from utils.reporting.execution_manager import ExecutionManager, list_executions

pytestmark = [pytest.mark.framework, pytest.mark.read_only]


@allure.feature("Framework")
@allure.story("Execution management")
class TestExecutionManager:
    def test_execution_dir_layout(self, execution: ExecutionManager) -> None:
        assert execution.execution_dir.exists()
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", execution.execution_dir.parent.name)
        assert execution.execution_dir.name.startswith("execution_")
        for sub in (
            "allure-results",
            "junit",
            "api/requests",
            "api/responses",
            "ui/screenshots",
            "ui/videos",
            "ui/traces",
            "e2e",
            "framework",
        ):
            assert (execution.execution_dir / sub).is_dir(), sub

    def test_new_executions_never_overwrite(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXECUTION_DIR", raising=False)
        first = ExecutionManager(reports_root=tmp_path)
        monkeypatch.delenv("EXECUTION_DIR", raising=False)
        second = ExecutionManager(reports_root=tmp_path)
        assert first.execution_dir != second.execution_dir
        assert len(list_executions(tmp_path)) == 2

    def test_workers_share_controller_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXECUTION_DIR", raising=False)
        controller = ExecutionManager(reports_root=tmp_path)
        assert os.environ["EXECUTION_DIR"] == str(controller.execution_dir)
        monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw3")
        worker = ExecutionManager(reports_root=tmp_path)
        assert worker.execution_dir == controller.execution_dir
        assert worker.log_file("ui").name == "gw3.log"

    def test_metadata_roundtrip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXECUTION_DIR", raising=False)
        manager = ExecutionManager(reports_root=tmp_path)
        manager.write_metadata(environment="qa")
        manager.write_metadata(browser="webkit")
        data = json.loads(manager.metadata_file.read_text())
        assert data["environment"] == "qa" and data["browser"] == "webkit"


@allure.feature("Framework")
@allure.story("Artifact management")
class TestArtifactManager:
    def test_safe_name(self) -> None:
        assert safe_name("test_login[Pixel 7/chrome]") == "test_login-Pixel-7-chrome"

    def test_artifact_names_are_unique_and_descriptive(self, artifacts: ArtifactManager) -> None:
        a = artifacts.screenshot_path("test_login_success", "chromium", "Pixel 7")
        b = artifacts.screenshot_path("test_login_success", "chromium", "Pixel 7")
        assert a != b
        assert "test_login_success" in a.name and "chromium" in a.name and "Pixel-7" in a.name
        assert a.parent.name == "screenshots"

    def test_json_artifacts_are_masked(self, artifacts: ArtifactManager) -> None:
        path = artifacts.write_json(artifacts.framework_path("masking_check"), {"password": "abc", "ok": 1})
        content = json.loads(path.read_text())
        assert content["password"] == "*****" and content["ok"] == 1

    def test_api_exchange_saved(self, artifacts: ArtifactManager) -> None:
        req, res = artifacts.save_api_exchange(
            "demo",
            {"method": "GET", "headers": {"Authorization": "Bearer x"}},
            {"status_code": 200, "body": {"token": "t"}},
        )
        assert req.exists() and res.exists()
        assert "Bearer x" not in req.read_text()
