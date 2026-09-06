"""
Execution summary builder.

Parses the JUnit XML produced by pytest and renders ``execution_summary.html``
plus ``execution_summary.json`` in the execution folder. Also appends a line
to ``reports/execution_history.csv`` so you can see trends across runs.
"""

from __future__ import annotations

import csv
import html
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.common.date_time_utils import format_duration
from utils.logging.logger import get_logger
from utils.reporting.execution_manager import REPORTS_ROOT, ExecutionManager

log = get_logger("SummaryBuilder")


@dataclass
class LayerCounts:
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    broken: int = 0


@dataclass
class ExecutionSummary:
    execution_id: str
    started_at: str
    finished_at: str
    duration: str
    environment: str
    browser: str
    device: str
    workers: Any
    reruns: Any
    exit_status: int
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    broken: int = 0
    layers: dict[str, LayerCounts] = field(default_factory=dict)
    failures: list[dict[str, str]] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        executed = self.total - self.skipped
        return round(100 * self.passed / executed, 1) if executed else 0.0


def _layer_of(classname: str) -> str:
    for layer in ("api", "ui", "e2e", "framework"):
        if classname.startswith(f"tests.{layer}.") or f".{layer}." in classname:
            return layer
    return "other"


def parse_junit(junit_file: Path) -> tuple[dict[str, LayerCounts], list[dict[str, str]]]:
    """Return per-layer counts and failure details from JUnit XML."""
    layers: dict[str, LayerCounts] = {name: LayerCounts() for name in ("api", "ui", "e2e", "framework")}
    failures: list[dict[str, str]] = []
    if not junit_file.exists():
        return layers, failures
    root = ET.parse(junit_file).getroot()
    # pytest-rerunfailures writes one <testcase> per attempt; keep only the
    # LAST attempt for each test so reruns are not counted twice.
    last_attempt: dict[str, ET.Element] = {}
    for case in root.iter("testcase"):
        last_attempt[f"{case.get('classname')}::{case.get('name')}"] = case
    for case in last_attempt.values():
        layer = _layer_of(case.get("classname", ""))
        counts = layers.setdefault(layer, LayerCounts())
        counts.total += 1
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        name = f"{case.get('classname')}::{case.get('name')}"
        if failure is not None:
            counts.failed += 1
            failures.append({"test": name, "kind": "failed", "message": (failure.get("message") or "")[:400]})
        elif error is not None:
            counts.broken += 1
            failures.append({"test": name, "kind": "broken", "message": (error.get("message") or "")[:400]})
        elif skipped is not None:
            counts.skipped += 1
        else:
            counts.passed += 1
    return layers, failures


def build_execution_summary(execution: ExecutionManager, duration_seconds: float, exit_status: int) -> Path:
    metadata = execution.read_metadata()
    layers, failures = parse_junit(execution.junit_file)
    summary = ExecutionSummary(
        execution_id=execution.execution_id,
        started_at=metadata.get("started_at", execution.started_at.isoformat(timespec="seconds")),
        finished_at=datetime.now().isoformat(timespec="seconds"),
        duration=format_duration(duration_seconds),
        environment=str(metadata.get("environment", "-")),
        browser=str(metadata.get("channel") or metadata.get("browser", "-")),
        device=str(metadata.get("device", "desktop")),
        workers=metadata.get("workers", 1),
        reruns=metadata.get("reruns", 0),
        exit_status=exit_status,
        layers=layers,
        failures=failures,
    )
    for counts in layers.values():
        summary.total += counts.total
        summary.passed += counts.passed
        summary.failed += counts.failed
        summary.skipped += counts.skipped
        summary.broken += counts.broken

    json_payload = asdict(summary)
    json_payload["pass_rate"] = summary.pass_rate
    (execution.execution_dir / "execution_summary.json").write_text(
        json.dumps(json_payload, indent=2), encoding="utf-8"
    )
    execution.summary_file.write_text(_render_html(summary), encoding="utf-8")
    execution.write_metadata(
        finished_at=summary.finished_at,
        duration=summary.duration,
        exit_status=exit_status,
        total=summary.total,
        passed=summary.passed,
        failed=summary.failed,
        skipped=summary.skipped,
        broken=summary.broken,
    )
    _append_history(summary)
    return execution.summary_file


def _append_history(summary: ExecutionSummary, history_file: Path = REPORTS_ROOT / "execution_history.csv") -> None:
    """Append to reports/execution_history.csv (created on first run)."""
    history_file.parent.mkdir(parents=True, exist_ok=True)
    new_file = not history_file.exists()
    with history_file.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if new_file:
            writer.writerow(
                [
                    "execution_id",
                    "started_at",
                    "duration",
                    "environment",
                    "browser",
                    "device",
                    "total",
                    "passed",
                    "failed",
                    "skipped",
                    "broken",
                    "pass_rate",
                ]
            )
        writer.writerow(
            [
                summary.execution_id,
                summary.started_at,
                summary.duration,
                summary.environment,
                summary.browser,
                summary.device,
                summary.total,
                summary.passed,
                summary.failed,
                summary.skipped,
                summary.broken,
                summary.pass_rate,
            ]
        )


def _render_html(s: ExecutionSummary) -> str:
    status_color = "#0a7a2f" if s.failed == 0 and s.broken == 0 else "#b00020"
    layer_rows = "".join(
        f"<tr><td>{html.escape(name.upper())}</td><td>{c.total}</td><td class='ok'>{c.passed}</td>"
        f"<td class='bad'>{c.failed}</td><td>{c.skipped}</td><td class='warn'>{c.broken}</td></tr>"
        for name, c in s.layers.items()
    )
    failure_rows = (
        "".join(
            f"<tr><td>{html.escape(f['kind'])}</td><td><code>{html.escape(f['test'])}</code></td>"
            f"<td>{html.escape(f['message'])}</td></tr>"
            for f in s.failures
        )
        or "<tr><td colspan='3'>No failures 🎉</td></tr>"
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Execution Summary - {html.escape(s.execution_id)}</title>
<style>
 body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f5f5f5;color:#222}}
 header{{background:#f40009;color:#fff;padding:18px 32px}} h1{{margin:0;font-size:22px}}
 main{{max-width:1000px;margin:24px auto;padding:0 16px}}
 .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:16px 0}}
 .card{{background:#fff;border-radius:8px;padding:14px;box-shadow:0 1px 3px #0002}}
 .card b{{display:block;font-size:26px}} .card span{{color:#666;font-size:12px}}
 table{{width:100%;border-collapse:collapse;background:#fff;box-shadow:0 1px 3px #0002;margin:12px 0}}
 th,td{{padding:8px 10px;border-bottom:1px solid #eee;text-align:left;font-size:14px}} th{{background:#fafafa}}
 .ok{{color:#0a7a2f}} .bad{{color:#b00020}} .warn{{color:#b26a00}}
 .status{{display:inline-block;padding:4px 10px;border-radius:12px;color:#fff;background:{status_color}}}
 dl{{display:grid;grid-template-columns:180px 1fr;gap:4px 12px;background:#fff;padding:14px;border-radius:8px}}
 dt{{color:#666}} code{{font-size:12px}}
</style></head><body>
<header><h1>Coca-Cola Automation - Execution Summary</h1></header>
<main>
 <p><span class="status">{'PASSED' if s.failed == 0 and s.broken == 0 else 'FAILED'}</span>
    &nbsp; Pass rate: <b>{s.pass_rate}%</b></p>
 <dl>
  <dt>Execution ID</dt><dd>{html.escape(s.execution_id)}</dd>
  <dt>Started</dt><dd>{html.escape(s.started_at)}</dd>
  <dt>Finished</dt><dd>{html.escape(s.finished_at)}</dd>
  <dt>Duration</dt><dd>{html.escape(s.duration)}</dd>
  <dt>Environment</dt><dd>{html.escape(s.environment)}</dd>
  <dt>Browser</dt><dd>{html.escape(s.browser)}</dd>
  <dt>Device</dt><dd>{html.escape(s.device)}</dd>
  <dt>Workers / Reruns</dt><dd>{html.escape(str(s.workers))} / {html.escape(str(s.reruns))}</dd>
  <dt>Exit status</dt><dd>{s.exit_status}</dd>
 </dl>
 <div class="cards">
  <div class="card"><b>{s.total}</b><span>Total</span></div>
  <div class="card"><b class="ok">{s.passed}</b><span>Passed</span></div>
  <div class="card"><b class="bad">{s.failed}</b><span>Failed</span></div>
  <div class="card"><b>{s.skipped}</b><span>Skipped</span></div>
  <div class="card"><b class="warn">{s.broken}</b><span>Broken</span></div>
 </div>
 <h2>By layer</h2>
 <table><tr><th>Layer</th><th>Total</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Broken</th></tr>{layer_rows}</table>
 <h2>Failures</h2>
 <table><tr><th>Kind</th><th>Test</th><th>Message</th></tr>{failure_rows}</table>
 <p style="color:#666;font-size:12px">Artifacts: allure-results/, junit/junit.xml, api/, ui/, e2e/, logs/ in this folder.
 Generate Allure: <code>allure generate allure-results -o allure-report --clean</code></p>
</main></body></html>"""
