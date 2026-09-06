#!/usr/bin/env python
"""
Generate API coverage from docs/api_inventory.yaml.

Outputs:
  * docs/api_coverage.md      - human-readable table + totals
  * docs/api_coverage.json    - machine-readable (for dashboards / CI)
  * prints the dependency chains from docs/api_dependency_map.yaml

Usage:
    python scripts/generate_api_inventory.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utils.common.file_utils import read_yaml  # noqa: E402

INVENTORY = PROJECT_ROOT / "docs" / "api_inventory.yaml"
DEPENDENCIES = PROJECT_ROOT / "docs" / "api_dependency_map.yaml"
COVERAGE_MD = PROJECT_ROOT / "docs" / "api_coverage.md"
COVERAGE_JSON = PROJECT_ROOT / "docs" / "api_coverage.json"


def main() -> int:
    endpoints = read_yaml(INVENTORY)["endpoints"]
    counts = Counter(e["test_status"] for e in endpoints)
    total = len(endpoints)
    placeholders = sum(1 for e in endpoints if str(e["endpoint"]).startswith("<"))
    by_test_file = {e["name"]: e.get("test_file") for e in endpoints}

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_endpoints": total,
        "automated": counts.get("automated", 0),
        "partially_automated": counts.get("partial", 0),
        "not_automated": counts.get("not_automated", 0),
        "placeholder_endpoints": placeholders,
        "coverage_percent": round(100 * counts.get("automated", 0) / total, 1) if total else 0.0,
        "endpoints": endpoints,
    }
    COVERAGE_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# API Coverage",
        "",
        f"_Generated {summary['generated_at']} from `docs/api_inventory.yaml`_",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total endpoints | {total} |",
        f"| Automated | {summary['automated']} |",
        f"| Partially automated | {summary['partially_automated']} |",
        f"| Not automated | {summary['not_automated']} |",
        f"| Still placeholders (`<...>`) | {placeholders} |",
        f"| Coverage | **{summary['coverage_percent']}%** |",
        "",
        "| Name | Method | Endpoint | Auth | Safety | Risk | Status | Test file |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for e in endpoints:
        lines.append(
            f"| {e['name']} | {e['method']} | `{e['endpoint']}` | {e['authentication']} | {e['safety']} | "
            f"{e['risk']} | {e['test_status']} | {e.get('test_file') or '-'} |"
        )
    lines += ["", "## Dependency chains", ""]
    for flow_name, flow in read_yaml(DEPENDENCIES)["flows"].items():
        lines.append(f"### {flow_name}")
        lines.append(f"_{flow['description']}_")
        lines.append("")
        lines.append("```text")
        lines.append("\n   ↓\n".join(f"{s['step']}. {s['call']}" for s in flow["steps"]))
        lines.append("```")
        lines.append("")
    COVERAGE_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"Total endpoints        : {total}")
    print(f"Automated endpoints    : {summary['automated']}")
    print(f"Partially automated    : {summary['partially_automated']}")
    print(f"Not automated          : {summary['not_automated']}")
    print(f"Placeholder endpoints  : {placeholders}")
    print(f"Coverage               : {summary['coverage_percent']}%")
    print(f"Written: {COVERAGE_MD.relative_to(PROJECT_ROOT)}, {COVERAGE_JSON.relative_to(PROJECT_ROOT)}")
    _ = by_test_file
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
