# Coca-Cola Automation Framework (Python + Playwright + Pytest)

A professional, beginner-friendly automation framework for **UI**, **API** and
**API + UI end-to-end** testing of `https://www.coca-cola.com/us/en`.

```text
                    COCA-COLA AUTOMATION
                             |
              +--------------+--------------+
              |              |              |
             API             UI            E2E
   api/clients, validators  ui/pages, components   tests/e2e + fixtures/e2e_fixtures
              |              |              |
              +--------------+--------------+
                             |
                       SHARED CORE  (utils/)
       +----------+----------+----------+----------+
       |          |          |          |          |
     Config     Data      Logging    Reporting   Security
   config/     test_data/  masking    Allure     safety guard
                             |
                           Pytest  (conftest.py, fixtures/)
                             |
                           CI/CD   (.github/workflows, ci/)
```

> **Important – no invented Coca-Cola APIs.** The real account/profile API
> endpoints are *not* public. Every real-site endpoint in this repo is a
> clearly marked placeholder such as `<AUTH_ENDPOINT>`. A tiny **local
> practice app** (`sandbox_app/`) with the same *shape* ships with the
> framework so every API/UI/E2E sample runs end-to-end today. When you
> discover an *authorized* endpoint, replace the placeholder
> (see [docs/api_discovery.md](docs/api_discovery.md)).

> **Interactive guide:** `getting_started/` contains a small React app
> (`App.tsx`) that walks you through install → write tests → run → reports.
> `cd getting_started && npm install && npm run dev`.

---

## Table of contents

1. [Installation](#1-installation)
2. [Quick start (5 minutes)](#2-quick-start-5-minutes)
3. [Running tests – all commands](#3-running-tests--all-commands)
4. [Project structure](#4-project-structure)
5. [Configuration & environments](#5-configuration--environments)
6. [Reports & artifacts](#6-reports--artifacts)
7. [Viewing Allure](#7-viewing-allure)
8. [Codegen → Page Object workflow](#8-codegen--page-object-workflow)
9. [API discovery (DevTools → cURL → test)](#9-api-discovery-devtools--curl--test)
10. [How to add things](#10-how-to-add-things) – Page Object, API client, tests, data, schema
11. [Mobile testing](#11-mobile-testing)
12. [Parallel execution & retries](#12-parallel-execution--retries)
13. [Safety classification & production protection](#13-safety-classification--production-protection)
14. [Security & secret masking](#14-security--secret-masking)
15. [Mocking](#15-mocking)
16. [Accessibility & broken links](#16-accessibility--broken-links)
17. [CI/CD](#17-cicd)
18. [Troubleshooting](#18-troubleshooting)

Deeper docs live in [`docs/`](docs/): architecture, api_automation,
ui_automation, e2e_automation, codegen_to_pom, api_discovery, ci_cd,
troubleshooting, api_inventory.yaml, api_dependency_map.yaml, api_coverage.md.

---

## 1. Installation

Requires **Python 3.11+**.

```bash
git clone <this-repo>
cd python_playwright_automation_practice

python -m venv .venv
```

Activate the virtual environment:

| OS | Command |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| Linux / macOS | `source .venv/bin/activate` |

Then:

```bash
pip install -r requirements.txt
playwright install                    # chromium, firefox, webkit
# Linux only, first time: playwright install --with-deps
cp .env.example .env                  # Windows: copy .env.example .env
```

Optional developer tooling (ruff / black / mypy):

```bash
pip install -r requirements-dev.txt
```

Optional Allure CLI (to *view* reports): https://allurereport.org/docs/install/
(`brew install allure`, `scoop install allure`, or `npm i -g allure-commandline`).

## 2. Quick start (5 minutes)

```bash
# Terminal 1 – start the local practice app (safe stand-in for the real APIs)
python sandbox_app/server.py            # http://127.0.0.1:8765

# Terminal 2 – run everything against it
pytest                                  # ENV=local is the default in .env
```

You will see something like:

```text
================== Coca-Cola Automation - execution artifacts ==================
Execution dir : reports/2026-09-06/execution_14-09-18
Summary       : reports/2026-09-06/execution_14-09-18/execution_summary.html
Allure results: reports/2026-09-06/execution_14-09-18/allure-results
JUnit XML     : reports/2026-09-06/execution_14-09-18/junit/junit.xml
114 passed, 18 skipped in 25.08s
```

Open `execution_summary.html` in a browser, or generate Allure (section 7).

To run the UI tests against the **real Coca-Cola site** (read-only tests only):

```bash
pytest tests/ui/content tests/ui/navigation --env=qa
```

## 3. Running tests – all commands

| Goal | Command |
|---|---|
| Everything | `pytest` |
| UI only | `pytest tests/ui` |
| API only | `pytest tests/api` |
| E2E only | `pytest tests/e2e` |
| Framework self-tests | `pytest tests/framework` |
| Smoke | `pytest -m smoke` |
| Regression | `pytest -m regression` |
| Combine markers | `pytest -m "api and smoke"` / `pytest -m "ui and not mocked"` |
| Chromium | `pytest --browser=chromium` |
| Chrome (branded) | `pytest --browser=chrome` |
| Edge (branded) | `pytest --browser=msedge` |
| Firefox | `pytest --browser=firefox` |
| WebKit (Safari engine) | `pytest --browser=webkit` |
| Several browsers | `pytest --browser=chromium --browser=firefox` |
| Mobile emulation | `pytest --device="Pixel 7"` / `pytest --device="iPhone 14"` |
| Headed (watch it) | `pytest --headed` |
| Slow motion | `pytest --headed --slowmo=500` |
| Environment | `pytest --env=qa` (or `ENV=qa pytest`) |
| Parallel | `pytest -n auto` / `pytest -n 4` |
| Retries | `pytest --reruns 1 --reruns-delay 2` |
| Artifact policy | `pytest --video-mode=always --trace-mode=always --screenshot-mode=always` |
| Only mocked tests | `pytest -m mocked` (or `--mocked-only`) |
| Real API tests only | `pytest tests/api -m "not mocked"` |
| Accessibility | `pytest -m accessibility` |
| Broken links | `pytest -m links` |
| Single test | `pytest tests/ui/auth/test_login_ui.py::TestLoginUi::test_login_success` |
| By keyword | `pytest -k "login and not negative"` |
| Options combined | `pytest tests/ui -m smoke --browser=firefox --device="Pixel 7" --headed -n 2 --reruns 1 --env=qa` |

Or use the wrapper: `python run_tests.py --suite ui --browser firefox --headed --allure-open`.

**Browser notes**
- `chrome` / `msedge` use the *installed* branded browser (Playwright channel).
  Install them with `playwright install chrome` / `playwright install msedge`.
- **WebKit is Playwright's Safari engine.** Playwright cannot drive a real
  Safari.app on macOS or Safari on iOS, nor a physical Android device.
- **Mobile = emulation**: Playwright emulates viewport, user agent, touch and
  device pixel ratio. It is *not* a physical phone or a cloud device farm.

## 4. Project structure

```text
├── api/                       # API LAYER (never imports Playwright)
│   ├── clients/               #   BaseAPIClient + AuthClient/UserClient/ProfileClient/ContentClient
│   ├── validators/            #   ResponseValidator, SchemaValidator, ContractValidator
│   ├── models/                #   ApiResponse / ApiRequestRecord
│   └── mocks/                 #   MockApiServer (API tests) + page.route helpers (UI tests)
├── ui/                        # UI LAYER (never performs HTTP requests)
│   ├── pages/                 #   BasePage + HomePage/LoginPage/SignupPage/ProfilePage/EditProfilePage
│   ├── components/            #   CookieBanner, Navigation, Modal, PopupHandler
│   └── utils/                 #   DeviceManager, AccessibilityChecker, LinkChecker
├── tests/
│   ├── api/{auth,profile,content,negative,contract,schema,mocked}/
│   ├── ui/{auth,profile,navigation,content,accessibility,links}/
│   ├── e2e/{api_to_ui,ui_to_api,full_flows}/
│   └── framework/             #   the framework tests itself
├── fixtures/                  # shared_fixtures, api_fixtures, ui_fixtures, e2e_fixtures
├── config/
│   ├── config.yaml            # browser, timeouts, artifact policies, retention
│   ├── environments/          # local.yaml, qa.yaml, staging.yaml, prod.yaml
│   └── devices/devices.yaml   # Pixel 5/7, Galaxy S23, iPhone 13/14/15, iPad
├── test_data/{api,ui,shared}/ # JSON / YAML / CSV test data (no secrets)
├── schemas/api/               # JSON Schemas + contracts/*.yaml
├── utils/
│   ├── config/                # config_reader.py, environment_manager.py
│   ├── data/                  # data_reader.py, test_data_factory.py
│   ├── logging/               # logger.py, masking.py
│   ├── reporting/             # execution_manager.py, allure_manager.py, summary_builder.py
│   ├── artifacts/             # artifact_manager.py
│   ├── security/              # safety_guard.py
│   ├── api/                   # api_helpers.py (cURL parser, perf assert)
│   └── common/                # helpers, date/time, files, runtime_context
├── sandbox_app/server.py      # local practice app (stand-in for unknown real APIs)
├── scripts/                   # discover_api.py, generate_api_inventory.py, cleanup_reports.py
├── docs/                      # guides + api_inventory.yaml + api_dependency_map.yaml + coverage
├── ci/                        # Jenkinsfile, azure-pipelines.yml
├── .github/workflows/automation.yml
├── getting_started/           # React "getting started" guide (App.tsx)
├── reports/                   # one unique folder per execution (git-ignored)
├── conftest.py  pytest.ini  run_tests.py  requirements*.txt  pyproject.toml  Makefile
└── .env.example  .gitignore
```

### The most important files

| File | What it does |
|---|---|
| `conftest.py` | Wires everything into pytest: CLI options (`--env`, `--device`, `--*-mode`), `--browser=chrome/msedge` translation, unique execution folder, Allure/JUnit paths, logging, safety guard, execution summary. |
| `pytest.ini` | Markers, defaults, JUnit settings. |
| `fixtures/ui_fixtures.py` | Browser/context/page fixtures: device emulation, video/trace/screenshot policies, Page Object factories. |
| `fixtures/api_fixtures.py` | Clients, `TokenManager`, `api_created_user` (create+cleanup), `mock_server`. Auto-skips when endpoints are placeholders. |
| `ui/pages/base_page.py` | Logged, auto-waiting actions; `expect_*` helpers; screenshots; new-tab handling. |
| `api/clients/base_client.py` | All HTTP verbs, auth provider, retries, timing, masked logging, request/response artifacts + Allure. |
| `api/clients/auth_client.py` | `AuthClient` + `TokenManager` (cache, expiry, refresh, thread-safe). |
| `utils/reporting/execution_manager.py` | `reports/YYYY-MM-DD/execution_HH-MM-SS/` – unique, xdist-safe, never overwritten. |
| `utils/artifacts/artifact_manager.py` | Naming + placement of screenshots/videos/traces/API dumps. |
| `utils/config/config_reader.py` | `config.yaml` + env-var overrides. |
| `utils/config/environment_manager.py` | Selects `local/qa/staging/prod`, exposes URLs, endpoints, safety flags, placeholder detection. |
| `utils/logging/masking.py` | Masks password/token/authorization/cookie/api_key/… everywhere. |
| `utils/security/safety_guard.py` | READ_ONLY / DATA_CREATING / DATA_MODIFYING / DESTRUCTIVE enforcement. |
| `utils/reporting/summary_builder.py` | `execution_summary.html/json` + `reports/execution_history.csv`. |

## 5. Configuration & environments

Precedence (highest wins): **CLI option → environment variable / `.env` → `config/environments/<env>.yaml` → `config/config.yaml`**.

`config/config.yaml` (excerpt):

```yaml
environment: qa
browser:   {name: chromium, headless: true, slow_mo: 0}
mobile:    {enabled: false, device: "Pixel 7"}
execution: {retries: 0, workers: 1}
artifacts: {screenshots: retain-on-failure, videos: retain-on-failure, traces: retain-on-failure}
reporting: {allure: true, junit: true}
security:  {mask_secrets: true}
retention: {enabled: false, days: 30, executions: 50}
```

Environments: `config/environments/{local,qa,staging,prod}.yaml` hold
`ui.base_url`, `api.base_url`, `api.endpoints.*` and `safety.*` flags.
Select with `--env=qa`, `ENV=qa` or `.env`.

Secrets only ever live in `.env` (git-ignored) – see `.env.example`.

## 6. Reports & artifacts

Every run creates a **unique** folder (never overwritten, xdist-safe):

```text
reports/
├── execution_history.csv                 # one row per run (trend)
└── 2026-09-06/
    └── execution_14-09-18/
        ├── allure-results/               # + environment.properties, executor.json
        ├── allure-report/                # after `allure generate`
        ├── junit/junit.xml
        ├── api/{requests,responses,logs}/   # masked JSON per call
        ├── ui/{screenshots,videos,traces,logs,accessibility,links}/
        ├── e2e/
        ├── framework/
        ├── logs/main.log, gw0.log ...    # per-worker logs
        ├── execution.json
        ├── execution_summary.json
        └── execution_summary.html        # ID, env, browser, device, totals per layer, failures
```

Artifact names carry test, browser, device, worker and timestamp:
`test_login_success__chromium__Pixel-7__gw0__14-08-38-840338.png`.

Policies (`always | retain-on-failure | never`) for screenshots, videos and
traces are set in `config.yaml`, `.env` (`VIDEO_MODE=…`) or CLI (`--video-mode=always`).
Traces include screenshots, DOM snapshots and sources:
`playwright show-trace reports/.../ui/traces/<file>.zip`.

Retention: `python scripts/cleanup_reports.py --dry-run` (deletes only when
`retention.enabled: true` / `RETENTION_ENABLED=true` / `--force`).

## 7. Viewing Allure

```bash
# after a run (paths are printed at the end of pytest output)
allure generate reports/2026-09-06/execution_14-09-18/allure-results \
       -o reports/2026-09-06/execution_14-09-18/allure-report --clean
allure open reports/2026-09-06/execution_14-09-18/allure-report

# or quick-serve the newest results
allure serve "$(ls -td reports/*/execution_* | head -1)/allure-results"

# or let the wrapper do it
python run_tests.py --suite ui --allure-open
```

Each test carries Feature / Story / Severity / Description / Steps plus labels
for environment, browser, device, layer and worker; attachments include
screenshots, video, trace, `test.log`, and every API request/response (masked).

## 8. Codegen → Page Object workflow

```bash
playwright codegen https://www.coca-cola.com/us/en
playwright codegen --device="Pixel 7" https://www.coca-cola.com/us/en
playwright codegen --target python-pytest -o generated.py http://127.0.0.1:8765/login
```

```text
Codegen → generated script → identify actions → locators to Page Object
→ test data to test_data/ → assertions into test → reusable methods
→ Allure metadata → logging → final maintainable test
```

Full worked example (login) in [docs/codegen_to_pom.md](docs/codegen_to_pom.md).

## 9. API discovery (DevTools → cURL → test)

```text
Open site → F12 → Network → Fetch/XHR → perform the UI action → click the request
→ inspect URL / method / headers / query / body / response / cookies / auth / correlation ids
→ right-click → Copy → Copy as cURL (bash) → python scripts/discover_api.py --curl "…"
```

The script masks secrets, drafts a client method, a test and an inventory
entry, and never sends the request. Step-by-step in
[docs/api_discovery.md](docs/api_discovery.md). Inventory and coverage:
`docs/api_inventory.yaml` → `python scripts/generate_api_inventory.py` →
`docs/api_coverage.md`.

## 10. How to add things

### New Page Object

```python
# ui/pages/offers_page.py
import re
from playwright.sync_api import Locator, Page, expect
from ui.pages.base_page import BasePage
from utils.common.runtime_context import RuntimeContext
from utils.reporting.allure_manager import step

class OffersPage(BasePage):
    PATH = "offers"

    def __init__(self, page: Page, context: RuntimeContext) -> None:
        super().__init__(page, context)
        self.heading: Locator = page.get_by_role("heading", name=re.compile("offers", re.I)).first
        self.claim_button: Locator = page.get_by_role("button", name=re.compile("claim", re.I)).first

    def expect_loaded(self) -> None:
        with step("Expect offers page loaded"):
            expect(self.heading).to_be_visible()

    def claim_first_offer(self) -> None:
        self.click(self.claim_button, "Claim offer button")
```

Add a fixture in `fixtures/ui_fixtures.py`:

```python
@pytest.fixture
def offers_page(page, runtime_context): return OffersPage(page, runtime_context)
```

### New API client

1. Add the path to `config/environments/<env>.yaml` → `api.endpoints.offers: /api/v1/offers`
2. Create `api/clients/offers_client.py`:

```python
from api.clients.base_client import AuthProvider, BaseAPIClient
from api.models.api_response import ApiResponse
from utils.config.environment_manager import Environment, get_environment

class OffersClient(BaseAPIClient):
    def __init__(self, environment: Environment | None = None, auth_provider: AuthProvider | None = None):
        self.environment = environment or get_environment()
        super().__init__(self.environment.api_base_url, name="OffersClient", auth_provider=auth_provider,
                         verify_ssl=self.environment.verify_ssl)

    def list_offers(self, **query) -> ApiResponse:
        return self.get(self.environment.endpoint("offers"), params=query or None, artifact_name="offers_list")
```

3. Add a fixture in `fixtures/api_fixtures.py` (use `require_real_api(environment, "offers")`).
4. Add an entry to `docs/api_inventory.yaml`.

### New UI test

```python
# tests/ui/content/test_offers_ui.py
import allure, pytest
pytestmark = [pytest.mark.ui, pytest.mark.content, pytest.mark.read_only]

@allure.feature("Offers")
class TestOffers:
    @allure.title("Offers page lists offers")
    @pytest.mark.smoke
    def test_offers_visible(self, offers_page):
        offers_page.open()
        offers_page.cookie_banner.accept_if_present()   # if the page has its own banner
        offers_page.expect_loaded()
        offers_page.screenshot("offers_loaded")
```

### New API test

```python
# tests/api/content/test_offers_api.py
import allure, pytest
from api.validators.response_validator import ResponseValidator
from api.validators.schema_validator import SchemaValidator
pytestmark = [pytest.mark.api, pytest.mark.content, pytest.mark.read_only]

@allure.feature("Offers API")
class TestOffersApi:
    @pytest.mark.smoke
    def test_list_offers(self, offers_client):
        response = offers_client.list_offers(page=1)
        ResponseValidator(response).status(200).content_type("application/json").list_not_empty("items")
        SchemaValidator.validate_response(response, "api/offers_list_schema.json")
```

### New E2E test

```python
# tests/e2e/api_to_ui/test_offer_claim.py
import allure, pytest
pytestmark = [pytest.mark.e2e, pytest.mark.data_modifying]

@allure.feature("E2E")
class TestOfferClaim:
    def test_claim_offer_visible_via_api(self, e2e_actors, offers_page, offers_client):
        e2e_actors.ui_login()                     # UI session via UI
        offers_page.open(); offers_page.claim_first_offer()
        response = offers_client.list_offers()    # API session via API token
        assert any(o["claimed"] for o in response.json()["items"]), response.failure_report()
```

### Adding test data

Put JSON/YAML/CSV under `test_data/{api,ui,shared}/` and load it:

```python
from utils.data.data_reader import DataReader
cases = DataReader.parametrize_cases("api/login_negative_cases.json")
@pytest.mark.parametrize("case", cases, ids=DataReader.case_ids(cases))
```

Dynamic data: `TestDataFactory.user()`, `.unique_email("label")`,
`.profile_update_payload()` – always prefixed `autotest_<timestamp>_<uuid>`.

### Adding a schema

Save `schemas/api/<name>_schema.json` (draft 2020-12) and call
`SchemaValidator.validate_response(response, "api/<name>_schema.json")`.
Optionally bundle status+headers+schema+SLA in `schemas/api/contracts/<name>.yaml`
and use `ContractValidator.validate(response, "api/contracts/<name>.yaml")`.

## 11. Mobile testing

```bash
pytest tests/ui --device="Pixel 7"
pytest tests/ui --device="iPhone 14" --browser=webkit    # iOS devices are best on WebKit
pytest tests/ui --device="Galaxy S23"
```

Devices come from `config/devices/devices.yaml` (Pixel 5, Pixel 7, Galaxy S23,
iPhone 13/14/15, iPad Pro 11) – add your own there. Any Playwright built-in
device name also works.

> Playwright mobile projects **emulate** mobile browsers. This is not the
> same as controlling a physical Android/iPhone device.

## 12. Parallel execution & retries

```bash
pytest -n auto                 # one worker per CPU
pytest -n 4 --dist loadfile    # keep a file's tests on one worker
pytest --reruns 1 --reruns-delay 2
```

Parallel safety is built in: the xdist controller creates the execution
folder and workers reuse it (`EXECUTION_DIR`), file names include the worker
id, logs are per-worker, Allure results are per-process files, and test data
is unique per test.

**Retries:** use `--reruns 1` for genuinely flaky infrastructure (network,
third-party widgets). Do **not** use retries to hide product defects or
selector problems – fix those. Reruns are visible in Allure and the summary.

## 13. Safety classification & production protection

Mark every test with one of `read_only`, `data_creating`, `data_modifying`,
`destructive`. `utils/security/safety_guard.py` skips tests the environment
does not allow (`safety.*` in `config/environments/<env>.yaml`). On **prod**
non-read-only tests are blocked unless *both* the YAML flag is enabled **and**
`ALLOW_PROD_WRITES=true` is set. Cleanup prefers the API (`api_created_user`
fixture deletes what it created).

## 14. Security & secret masking

- Credentials live in `.env` only; `.env` is git-ignored; `.env.example` has placeholders.
- `utils/logging/masking.py` masks `password, token, authorization, cookie,
  api_key, client_secret, access_token, refresh_token, …` in logs, API
  artifacts, Allure attachments and URLs (`?token=…`), plus JWT-looking strings.
- Page Objects log passwords as `*****` (`fill(..., secret=True)`).
- Never automate around CAPTCHA/WAF/bot protection/rate limits; only test
  what you are authorized to test.

## 15. Mocking

- **API tests:** `mock_server` fixture (`api/mocks/mock_server.py`) – a local
  HTTP server with `add_route(...)` and request recording. Mark tests `mocked`.
- **UI tests:** `api/mocks/ui_route_mocks.py` – `mock_json_response(page, "**/api/x", {...})`,
  `mock_failure(...)`, `block_common_third_parties(page)`.
- Real vs mocked never mix: `pytest -m "api and not mocked"` for integration,
  `pytest -m mocked` / `--mocked-only` for mocks.

## 16. Accessibility & broken links

```bash
pytest -m accessibility        # axe-core, WCAG A / AA (ui/utils/accessibility.py)
pytest -m links                # extract → normalise → dedupe → HEAD/GET → report (ui/utils/link_checker.py)
```

Both are optional utilities; the framework does not depend on them.

## 17. CI/CD

- **GitHub Actions:** `.github/workflows/automation.yml` – matrix per
  suite/browser, JUnit publishing, artifact upload, merged Allure report,
  optional GitHub Pages history.
- **Jenkins:** `ci/Jenkinsfile` – parameters, credentials binding, JUnit,
  Allure plugin, HTML summary.
- **Azure DevOps:** `ci/azure-pipelines.yml` – PublishTestResults, pipeline artifacts, Allure CLI.

All pipelines: install deps → `playwright install --with-deps` → run tests →
Allure results → JUnit → publish artifacts/reports. Details in [docs/ci_cd.md](docs/ci_cd.md).

## 18. Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md). Most common:

| Symptom | Fix |
|---|---|
| `Executable doesn't exist` | `playwright install` (Linux: `--with-deps`) |
| Tests skipped: "Real API base URL not configured" | Expected until you replace `<REAL_API_BASE_URL>` in `config/environments/<env>.yaml` |
| Tests skipped with `[SAFETY]` | Environment forbids that safety level (by design on prod) |
| Cookie banner blocks clicks | Use `home_page.open_and_prepare()` / `page.cookie_banner.accept_if_present()` |
| `allure: command not found` | Install the Allure CLI (section 1) |
| Slow tests | Check locators are regex (`re.compile`) not strings; avoid `time.sleep` |
