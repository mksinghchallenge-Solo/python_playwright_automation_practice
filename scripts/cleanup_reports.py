#!/usr/bin/env python
"""
Report retention - delete old execution folders under reports/.

Nothing is deleted unless retention is ENABLED (config.yaml retention.enabled,
RETENTION_ENABLED=true, or --force). Use --dry-run to preview.

Rules (both applied when set):
  * RETENTION_DAYS        keep executions newer than N days
  * RETENTION_EXECUTIONS  keep at most the N most recent executions

Usage:
    python scripts/cleanup_reports.py --dry-run
    python scripts/cleanup_reports.py --days 30 --executions 50 --force
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utils.common.file_utils import directory_size_bytes, remove_directory  # noqa: E402
from utils.config.config_reader import get_config  # noqa: E402
from utils.reporting.execution_manager import REPORTS_ROOT, list_executions  # noqa: E402


def select_for_deletion(executions: list[Path], days: int | None, keep: int | None) -> list[Path]:
    """Executions are sorted oldest -> newest."""
    doomed: set[Path] = set()
    if days is not None:
        cutoff = time.time() - days * 86400
        doomed.update(p for p in executions if p.stat().st_mtime < cutoff)
    if keep is not None and len(executions) > keep:
        doomed.update(executions[: len(executions) - keep])
    return sorted(doomed)


def main() -> int:
    config = get_config()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=config.get("retention.days"))
    parser.add_argument("--executions", type=int, default=config.get("retention.executions"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="delete even if retention.enabled is false")
    parser.add_argument("--reports-root", default=str(REPORTS_ROOT))
    args = parser.parse_args()

    enabled = bool(config.get("retention.enabled", False)) or args.force
    executions = list_executions(Path(args.reports_root))
    doomed = select_for_deletion(executions, args.days, args.executions)

    print(f"Executions found : {len(executions)}")
    print(f"Retention        : days={args.days} executions={args.executions} enabled={enabled}")
    print(f"To delete        : {len(doomed)}")
    for path in doomed:
        print(f"  - {path}  ({directory_size_bytes(path) / 1_000_000:.1f} MB)")
    if args.dry_run:
        print("Dry run - nothing deleted.")
        return 0
    if not enabled:
        print("Retention is DISABLED (set retention.enabled: true or RETENTION_ENABLED=true or --force). Nothing deleted.")
        return 0
    for path in doomed:
        remove_directory(path)
        day_dir = path.parent
        if day_dir.exists() and not any(day_dir.iterdir()):
            day_dir.rmdir()
    print(f"Deleted {len(doomed)} execution folder(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
