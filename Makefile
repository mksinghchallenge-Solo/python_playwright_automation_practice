# Convenience targets (Linux/macOS). Windows users: run the commands directly.
.PHONY: install browsers app test ui api e2e framework smoke allure lint clean

install:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

browsers:
	. .venv/bin/activate && playwright install --with-deps

app:
	. .venv/bin/activate && python sandbox_app/server.py

test:
	. .venv/bin/activate && pytest

ui:
	. .venv/bin/activate && pytest tests/ui

api:
	. .venv/bin/activate && pytest tests/api

e2e:
	. .venv/bin/activate && pytest tests/e2e

framework:
	. .venv/bin/activate && pytest tests/framework

smoke:
	. .venv/bin/activate && pytest -m smoke -n auto

allure:
	. .venv/bin/activate && python run_tests.py --suite framework --allure-open

lint:
	. .venv/bin/activate && ruff check . && black --check . && mypy utils api ui fixtures scripts run_tests.py conftest.py

clean:
	. .venv/bin/activate && python scripts/cleanup_reports.py --dry-run
