#!/usr/bin/env python
"""
Beginner-friendly test runner (thin wrapper around pytest).

Examples:
    python run_tests.py                          # everything (local env)
    python run_tests.py --suite ui --browser firefox --headed
    python run_tests.py --suite api --env qa
    python run_tests.py --suite e2e --device "Pixel 7"
    python run_tests.py --markers "api and smoke" --parallel auto --reruns 1
    python run_tests.py --suite ui --allure-open   # generate + open Allure afterwards

Anything after "--" is passed straight to pytest:
    python run_tests.py --suite ui -- -k login -x
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SUITES = {"all": "tests", "ui": "tests/ui", "api": "tests/api", "e2e": "tests/e2e", "framework": "tests/framework"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", choices=SUITES, default="all")
    parser.add_argument("--env", choices=["local", "qa", "staging", "prod"], default=None)
    parser.add_argument("--browser", default=None, help="chromium | chrome | msedge | firefox | webkit")
    parser.add_argument("--device", default=None, help='e.g. "Pixel 7", "iPhone 14"')
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--slowmo", type=int, default=None)
    parser.add_argument("--markers", "-m", default=None, help='pytest -m expression, e.g. "api and smoke"')
    parser.add_argument("--parallel", "-n", default=None, help="number of workers or 'auto'")
    parser.add_argument("--reruns", type=int, default=None)
    parser.add_argument("--allure-generate", action="store_true", help="run 'allure generate' after tests")
    parser.add_argument("--allure-open", action="store_true", help="generate and open the Allure report")
    args, passthrough = parser.parse_known_args()
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]

    command = [sys.executable, "-m", "pytest", SUITES[args.suite]]
    if args.env:
        command += ["--env", args.env]
    if args.browser:
        command += [f"--browser={args.browser}"]
    if args.device:
        command += [f"--device={args.device}"]
    if args.headed:
        command.append("--headed")
    if args.slowmo:
        command += [f"--slowmo={args.slowmo}"]
    if args.markers:
        command += ["-m", args.markers]
    if args.parallel:
        command += ["-n", str(args.parallel)]
    if args.reruns is not None:
        command += ["--reruns", str(args.reruns)]
    command += passthrough

    print("Running:", " ".join(command))
    result = subprocess.run(command, cwd=PROJECT_ROOT)

    if args.allure_generate or args.allure_open:
        execution_dir = os.environ.get("EXECUTION_DIR") or _latest_execution()
        if not execution_dir:
            print("No execution directory found - skipping Allure generation")
            return result.returncode
        allure = shutil.which("allure")
        if not allure:
            print("Allure CLI not found on PATH. Install: https://allurereport.org/docs/install/")
            return result.returncode
        results = Path(execution_dir) / "allure-results"
        report = Path(execution_dir) / "allure-report"
        subprocess.run([allure, "generate", str(results), "-o", str(report), "--clean"], check=False)
        print(f"Allure report: {report / 'index.html'}")
        if args.allure_open:
            subprocess.run([allure, "open", str(report)], check=False)
    return result.returncode


def _latest_execution() -> str | None:
    sys.path.insert(0, str(PROJECT_ROOT))
    from utils.reporting.execution_manager import list_executions

    executions = list_executions()
    return str(executions[-1]) if executions else None


if __name__ == "__main__":
    raise SystemExit(main())
