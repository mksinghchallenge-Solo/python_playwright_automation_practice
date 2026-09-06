# Architecture

## Layers and boundaries

```text
Shared Core (utils/, config/, test_data/, schemas/)
        ↓                         ↓
API clients (api/)        UI Page Objects (ui/)
        \                         /
                  E2E (tests/e2e + fixtures/e2e_fixtures.py)
                          ↓
                       Pytest (conftest.py, fixtures/)
                          ↓
                        CI/CD
```

| Rule | Where it is enforced |
|---|---|
| No Playwright inside API clients | `api/` never imports `playwright` (grep-checked in `tests/framework`) |
| No HTTP requests inside Page Objects | `ui/pages` never imports `requests`/`httpx` |
| No environment URLs inside tests | tests use `environment.ui_base_url` / Page Object `PATH` / `endpoint("name")` |
| No secrets in code | `.env` + masking + `.gitignore` |
| No duplicated cookie handling | `ui/components/cookie_banner.py`, called from `open_and_prepare()` |
| No arbitrary sleeps | `expect(...)` + auto-waiting; `is_visible(timeout)` for optional elements |
| No invented endpoints | placeholders `<...>` + `require_real_api()` auto-skip |
| Never overwrite executions | `ExecutionManager` numeric suffix + `EXECUTION_DIR` sharing |

## Request flow – API test

```text
test → fixture (profile_client) → ProfileClient.get_profile()
     → BaseAPIClient.request()  → AuthProvider.auth_headers() (TokenManager)
     → requests.Session (retries for GET/HEAD only)
     → ApiResponse (timing) → log (masked) → artifact json → Allure attachment
     → ResponseValidator / SchemaValidator / ContractValidator
```

## Request flow – UI test

```text
test → fixture (login_page) → LoginPage(page, runtime_context)
     ↑ page fixture: context (device options, video dir, tracing) → new_page
     → BasePage.fill/click (logged, Allure step) → expect(...)
     → teardown: screenshot/trace/video per policy → ArtifactManager paths → Allure
```

## Execution lifecycle

1. `pytest_load_initial_conftests` – translate `--browser=chrome|msedge` → chromium + channel.
2. `pytest_configure` – resolve env, create `reports/<date>/execution_<time>/`, point Allure/JUnit there,
   attach file logging, write `environment.properties`, `executor.json`, `execution.json`.
3. `pytest_collection_modifyitems` – add layer markers by path, honour `--mocked-only`.
4. `pytest_runtest_setup` – safety guard.
5. autouse `_test_context` – log context, Allure labels, per-test log attachment.
6. `pytest_runtest_makereport` – outcome exposed for fixtures (screenshot on failure...).
7. `pytest_sessionfinish` – `execution_summary.html/json`, `execution_history.csv`.

## Extending without redesign

* New page → subclass `BasePage`, add fixture.
* New API area → subclass `BaseAPIClient`, add endpoint key + fixture + inventory entry.
* New environment → new YAML in `config/environments/` + add to `SUPPORTED_ENVIRONMENTS`.
* New device → entry in `config/devices/devices.yaml`.
* New artifact type → method on `ArtifactManager`.
* New validation → method on `ResponseValidator` (chainable).
