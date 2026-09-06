/**
 * Coca-Cola Automation Framework – interactive Getting Started guide.
 *
 * Launch:   cd getting_started && npm install && npm run dev
 * Purpose:  walk a complete beginner from "clone" to "green Allure report"
 *           for UI, API and API+UI (E2E) tests, step by step.
 *
 * Everything shown here mirrors README.md and docs/. Nothing is executed from
 * the browser – copy the commands into your terminal.
 */

import { useEffect, useMemo, useState } from "react";

type OS = "windows" | "mac" | "linux";

interface Step {
  id: string;
  title: string;
  render: (ctx: Ctx) => JSX.Element;
}

interface Ctx {
  os: OS;
  setOs: (os: OS) => void;
}

/* ------------------------------------------------------------------ utils */

function Code({ children, lang = "bash" }: { children: string; lang?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(children.trim());
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      /* clipboard may be unavailable in iframes – ignore */
    }
  };
  return (
    <pre data-lang={lang}>
      <button className="copy" onClick={copy}>
        {copied ? "Copied ✓" : "Copy"}
      </button>
      <code>{children.trim()}</code>
    </pre>
  );
}

function Note({ children, ok = false }: { children: React.ReactNode; ok?: boolean }) {
  return <div className={`note${ok ? " ok" : ""}`}>{children}</div>;
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

function OsTabs({ os, setOs }: Ctx) {
  const items: [OS, string][] = [
    ["windows", "Windows (PowerShell)"],
    ["mac", "macOS"],
    ["linux", "Linux"],
  ];
  return (
    <div className="tabs">
      {items.map(([key, label]) => (
        <button key={key} className={os === key ? "active" : ""} onClick={() => setOs(key)}>
          {label}
        </button>
      ))}
    </div>
  );
}

const activate = (os: OS) =>
  os === "windows" ? ".venv\\Scripts\\Activate.ps1" : "source .venv/bin/activate";
const copyEnv = (os: OS) => (os === "windows" ? "copy .env.example .env" : "cp .env.example .env");

/* ------------------------------------------------------------------ steps */

const steps: Step[] = [
  {
    id: "overview",
    title: "What you are getting",
    render: () => (
      <>
        <h2>Welcome 👋</h2>
        <p>
          This is a production-quality <b>Python + Playwright + Pytest</b> framework for testing{" "}
          <code>https://www.coca-cola.com/us/en</code> at three levels:
        </p>
        <div className="tree">{`                    COCA-COLA AUTOMATION
                             |
              +--------------+--------------+
              |              |              |
             API             UI            E2E
              |              |              |
              +--------------+--------------+
                             |
                       SHARED CORE
       Config · Data · Logging · Reporting · Security
                             |
                           Pytest
                             |
                           CI/CD`}</div>
        <Card title="What is included">
          <table>
            <tbody>
              <tr><th>UI</th><td>Page Object Model, cookie/popup/new-tab handlers, desktop + mobile emulation, screenshots / videos / traces</td></tr>
              <tr><th>API</th><td>BaseAPIClient (all verbs), token manager, response / schema / contract validators, mock server</td></tr>
              <tr><th>E2E</th><td>API setup → UI verify, UI update → API verify, full flows with cleanup</td></tr>
              <tr><th>Reporting</th><td>Allure, JUnit XML, execution_summary.html, unique folder per run, history CSV</td></tr>
              <tr><th>Safety</th><td>Secret masking, READ_ONLY / DATA_CREATING / DATA_MODIFYING / DESTRUCTIVE guard, prod protection</td></tr>
              <tr><th>CI</th><td>GitHub Actions, Jenkins, Azure DevOps</td></tr>
            </tbody>
          </table>
        </Card>
        <Note>
          <b>No invented Coca-Cola APIs.</b> The real account APIs are not public, so every real endpoint
          is a placeholder like <code>&lt;AUTH_ENDPOINT&gt;</code>. A tiny <b>local practice app</b>{" "}
          (<code>sandbox_app/server.py</code>) with the same shape is bundled so all samples run today.
          When you discover an authorized endpoint you replace the placeholder – that is all.
        </Note>
      </>
    ),
  },
  {
    id: "install",
    title: "Install",
    render: (ctx) => (
      <>
        <h2>Step 1 – Install</h2>
        <p>Requires <b>Python 3.11+</b> and Git. Pick your OS:</p>
        <OsTabs {...ctx} />
        <Card title="1. Clone and create a virtual environment">
          <Code>{`git clone <your-repo-url> python_playwright_automation_practice
cd python_playwright_automation_practice
python -m venv .venv
${activate(ctx.os)}`}</Code>
        </Card>
        <Card title="2. Install Python packages">
          <Code>{`pip install --upgrade pip
pip install -r requirements.txt`}</Code>
        </Card>
        <Card title="3. Install Playwright browsers (Chromium, Firefox, WebKit)">
          <Code>{ctx.os === "linux" ? "playwright install --with-deps" : "playwright install"}</Code>
          <p>
            Optional branded browsers: <code>playwright install chrome</code>, <code>playwright install msedge</code>.
            <br />
            <b>WebKit is Playwright's Safari engine</b> – Playwright cannot drive a real Safari app or a
            physical phone.
          </p>
        </Card>
        <Card title="4. Create your .env (secrets live only here)">
          <Code>{copyEnv(ctx.os)}</Code>
          <p>
            The defaults point to the local practice app (<code>ENV=local</code>) with demo credentials.
            Never commit <code>.env</code> – it is git-ignored.
          </p>
        </Card>
        <Card title="5. (Optional) Allure CLI – to view reports">
          <Code>{ctx.os === "windows" ? "scoop install allure   # or: npm i -g allure-commandline" : ctx.os === "mac" ? "brew install allure     # or: npm i -g allure-commandline" : "npm i -g allure-commandline   # or download from allurereport.org"}</Code>
        </Card>
        <Card title="6. (Optional) developer tooling">
          <Code>{`pip install -r requirements-dev.txt   # ruff, black, mypy`}</Code>
        </Card>
      </>
    ),
  },
  {
    id: "first-run",
    title: "First run (5 min)",
    render: (ctx) => (
      <>
        <h2>Step 2 – Your first green run</h2>
        <Card title="Terminal 1 – start the practice app">
          <Code>{`${activate(ctx.os)}
python sandbox_app/server.py        # → http://127.0.0.1:8765`}</Code>
        </Card>
        <Card title="Terminal 2 – run the whole suite">
          <Code>{`${activate(ctx.os)}
pytest`}</Code>
          <p>Expected tail of the output:</p>
          <Code lang="text">{`================== Coca-Cola Automation - execution artifacts ==================
Execution dir : reports/2026-09-06/execution_14-09-18
Summary       : reports/2026-09-06/execution_14-09-18/execution_summary.html
Allure results: reports/2026-09-06/execution_14-09-18/allure-results
JUnit XML     : reports/2026-09-06/execution_14-09-18/junit/junit.xml
112 passed, 18 skipped`}</Code>
        </Card>
        <Note ok>
          Skipped tests are expected: the <code>httpbin.org</code> examples skip without internet, and any
          test that needs a real Coca-Cola endpoint skips until you replace its placeholder.
        </Note>
        <Card title="Run against the real website (read-only UI checks)">
          <Code>{`pytest tests/ui/content tests/ui/navigation --env=qa --headed`}</Code>
        </Card>
      </>
    ),
  },
  {
    id: "structure",
    title: "Project tour",
    render: () => (
      <>
        <h2>Step 3 – Where things live</h2>
        <div className="tree">{`api/                 API layer – clients, validators, models, mocks  (never imports Playwright)
ui/                  UI layer – pages (POM), components, utils      (never sends HTTP)
tests/api|ui|e2e|framework
fixtures/            shared / api / ui / e2e pytest fixtures
config/              config.yaml, environments/{local,qa,staging,prod}.yaml, devices/devices.yaml
test_data/           JSON / YAML / CSV data (no secrets)
schemas/api/         JSON Schemas + contracts/*.yaml
utils/               config, data, logging(+masking), reporting, artifacts, security, common
sandbox_app/         local practice app
scripts/             discover_api.py, generate_api_inventory.py, cleanup_reports.py
docs/                guides, api_inventory.yaml, api_dependency_map.yaml, api_coverage.md
reports/             one unique folder per execution (git-ignored)
conftest.py          wires everything into pytest
pytest.ini           markers + defaults`}</div>
        <Card title="Files to read first">
          <table>
            <tbody>
              <tr><td><code>conftest.py</code></td><td>CLI options, execution folder, Allure/JUnit paths, logging, safety guard, summary</td></tr>
              <tr><td><code>ui/pages/base_page.py</code></td><td>logged actions + <code>expect_*</code> helpers used by every Page Object</td></tr>
              <tr><td><code>api/clients/base_client.py</code></td><td>every HTTP verb, auth, retries, timing, masked logging, artifacts</td></tr>
              <tr><td><code>fixtures/ui_fixtures.py</code></td><td>browser/context/page with device emulation and artifact policies</td></tr>
              <tr><td><code>fixtures/api_fixtures.py</code></td><td>clients, TokenManager, created-user-with-cleanup, mock server</td></tr>
              <tr><td><code>utils/reporting/execution_manager.py</code></td><td><code>reports/YYYY-MM-DD/execution_HH-MM-SS/</code>, never overwritten</td></tr>
            </tbody>
          </table>
        </Card>
      </>
    ),
  },
  {
    id: "write-ui",
    title: "Write a UI test",
    render: () => (
      <>
        <h2>Step 4 – Write a UI test (Page Object Model)</h2>
        <Card title="a) Record with Codegen (optional but recommended)">
          <Code>{`playwright codegen --target python-pytest -o generated.py http://127.0.0.1:8765/login
# real site:  playwright codegen https://www.coca-cola.com/us/en
# mobile:     playwright codegen --device="Pixel 7" https://www.coca-cola.com/us/en`}</Code>
          <p>
            Then convert: locators → Page Object, data → <code>test_data/</code> or <code>.env</code>,
            assertions → test, add Allure + logging. Full walk-through: <code>docs/codegen_to_pom.md</code>.
          </p>
        </Card>
        <Card title="b) Create the Page Object – ui/pages/offers_page.py">
          <Code lang="python">{`import re
from playwright.sync_api import Locator, Page, expect
from ui.pages.base_page import BasePage
from utils.common.runtime_context import RuntimeContext
from utils.reporting.allure_manager import step

class OffersPage(BasePage):
    PATH = "offers"                                   # relative to the environment base URL

    def __init__(self, page: Page, context: RuntimeContext) -> None:
        super().__init__(page, context)
        self.heading: Locator = page.get_by_role("heading", name=re.compile("offers", re.I)).first
        self.claim_button: Locator = page.get_by_role("button", name=re.compile("claim", re.I)).first

    def expect_loaded(self) -> None:
        with step("Expect offers page loaded"):
            expect(self.heading).to_be_visible()

    def claim_first_offer(self) -> None:
        self.click(self.claim_button, "Claim offer button")   # logged + Allure step`}</Code>
        </Card>
        <Card title="c) Register a fixture – fixtures/ui_fixtures.py">
          <Code lang="python">{`@pytest.fixture
def offers_page(page: Page, runtime_context: RuntimeContext) -> OffersPage:
    return OffersPage(page, runtime_context)`}</Code>
        </Card>
        <Card title="d) Write the test – tests/ui/content/test_offers_ui.py">
          <Code lang="python">{`import allure, pytest
pytestmark = [pytest.mark.ui, pytest.mark.content, pytest.mark.read_only]

@allure.feature("Offers")
@allure.story("Browse offers")
class TestOffers:
    @allure.title("Offers page lists offers")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.smoke
    def test_offers_visible(self, offers_page):
        offers_page.open()
        offers_page.expect_loaded()
        offers_page.screenshot("offers_loaded")`}</Code>
        </Card>
        <Note>
          Rules: locator priority <code>get_by_role → get_by_label → get_by_placeholder → get_by_test_id → get_by_text → CSS → XPath</code>;
          never <code>time.sleep()</code>; never hardcode URLs or credentials; cookie handling only via{" "}
          <code>CookieBanner</code>.
        </Note>
      </>
    ),
  },
  {
    id: "write-api",
    title: "Write an API test",
    render: () => (
      <>
        <h2>Step 5 – Discover and write an API test</h2>
        <Card title="a) Discover the endpoint (Chrome DevTools)">
          <div className="tree">{`Open website → F12 → Network → Fetch/XHR → perform the UI action
→ click the request → inspect URL, method, headers, query, body, response, cookies, auth, X-Request-Id
→ right-click → Copy → Copy as cURL (bash)`}</div>
          <Code>{`python scripts/discover_api.py --name get_profile --curl "curl 'https://<host>/api/v1/users/me' -H 'authorization: Bearer …'"`}</Code>
          <p>
            The script masks secrets, drafts a client method, a test and an inventory entry. It never sends the
            request. <b>Only automate endpoints you are authorized to test.</b>
          </p>
        </Card>
        <Card title="b) Put the path in config – config/environments/qa.yaml">
          <Code lang="yaml">{`api:
  base_url: "https://<host>"          # was <REAL_API_BASE_URL>
  endpoints:
    profile: "/api/v1/users/me"       # was <PROFILE_ENDPOINT>`}</Code>
        </Card>
        <Card title="c) Client method – api/clients/offers_client.py">
          <Code lang="python">{`from api.clients.base_client import AuthProvider, BaseAPIClient
from api.models.api_response import ApiResponse
from utils.config.environment_manager import Environment, get_environment

class OffersClient(BaseAPIClient):
    def __init__(self, environment: Environment | None = None, auth_provider: AuthProvider | None = None):
        self.environment = environment or get_environment()
        super().__init__(self.environment.api_base_url, name="OffersClient",
                         auth_provider=auth_provider, verify_ssl=self.environment.verify_ssl)

    def list_offers(self, **query) -> ApiResponse:
        return self.get(self.environment.endpoint("offers"), params=query or None, artifact_name="offers_list")`}</Code>
        </Card>
        <Card title="d) Test – tests/api/content/test_offers_api.py">
          <Code lang="python">{`import allure, pytest
from api.validators.response_validator import ResponseValidator
from api.validators.schema_validator import SchemaValidator
pytestmark = [pytest.mark.api, pytest.mark.content, pytest.mark.read_only]

@allure.feature("Offers API")
class TestOffersApi:
    @pytest.mark.smoke
    def test_list_offers(self, offers_client):
        response = offers_client.list_offers(page=1)
        (ResponseValidator(response)
            .status(200)
            .content_type("application/json")
            .correlation_id_present()
            .response_time_below(2000)
            .list_not_empty("items"))
        SchemaValidator.validate_response(response, "api/offers_list_schema.json")`}</Code>
        </Card>
        <Card title="e) Keep the inventory current">
          <Code>{`# add an entry to docs/api_inventory.yaml, then:
python scripts/generate_api_inventory.py     # → docs/api_coverage.md (total / automated / partial / not automated)`}</Code>
        </Card>
      </>
    ),
  },
  {
    id: "write-e2e",
    title: "Write an API + UI test",
    render: () => (
      <>
        <h2>Step 6 – Combine API and UI (E2E)</h2>
        <Card title="Patterns">
          <div className="tree">{`API → UI      API creates user → UI login → open profile → verify API-created data
UI → API      UI edits profile → API GET profile → verify backend
Full flow     API setup → UI action → API validation → cleanup`}</div>
        </Card>
        <Card title="Building blocks you already have">
          <table>
            <tbody>
              <tr><td><code>api_created_user</code></td><td>creates a unique user via API and deletes it afterwards (API cleanup)</td></tr>
              <tr><td><code>e2e_actors</code></td><td>user + authenticated <code>ProfileClient</code> + UI pages; <code>ui_login()</code> logs in through the UI</td></tr>
            </tbody>
          </table>
        </Card>
        <Card title="Example – tests/e2e/ui_to_api/test_offer_claim.py">
          <Code lang="python">{`import allure, pytest
from api.validators.response_validator import ResponseValidator
pytestmark = [pytest.mark.e2e, pytest.mark.data_modifying]

@allure.feature("E2E")
@allure.story("UI action → API verification")
class TestOfferClaim:
    def test_claim_visible_in_api(self, e2e_actors, offers_page, offers_client):
        e2e_actors.ui_login()                      # browser session via the UI
        offers_page.open()
        offers_page.claim_first_offer()

        response = offers_client.list_offers()     # API session via API token
        ResponseValidator(response).status(200).field_matches(
            "items", lambda items: any(i.get("claimed") for i in items), "an offer is claimed")`}</Code>
        </Card>
        <Note>
          API tokens and browser sessions are <b>not</b> assumed interchangeable. The framework never injects an
          API token into the browser; add an explicit helper only if the real application supports it.
        </Note>
      </>
    ),
  },
  {
    id: "run",
    title: "Run tests",
    render: () => (
      <>
        <h2>Step 7 – Run anything, anywhere</h2>
        <Card title="By layer">
          <Code>{`pytest                 # everything
pytest tests/ui        # UI
pytest tests/api       # API
pytest tests/e2e       # API + UI
pytest tests/framework # the framework tests itself`}</Code>
        </Card>
        <Card title="By marker">
          <Code>{`pytest -m smoke
pytest -m regression
pytest -m "api and smoke"
pytest -m "ui and not mocked"
pytest -m accessibility          # axe-core WCAG A/AA
pytest -m links                  # broken-link check`}</Code>
        </Card>
        <Card title="Browsers & devices">
          <Code>{`pytest --browser=chromium
pytest --browser=chrome          # branded Chrome (playwright install chrome)
pytest --browser=msedge          # branded Edge
pytest --browser=firefox
pytest --browser=webkit          # Safari engine
pytest --device="Pixel 7"        # mobile emulation (not a physical phone)
pytest --device="iPhone 14" --browser=webkit`}</Code>
        </Card>
        <Card title="Debug, parallel, retries, environment">
          <Code>{`pytest --headed --slowmo=500
pytest -n auto                   # parallel (pytest-xdist)
pytest --reruns 1 --reruns-delay 2
pytest --env=qa                  # or ENV=qa in .env
pytest --video-mode=always --trace-mode=always --screenshot-mode=always
pytest tests/ui -m smoke --browser=firefox --device="Pixel 7" --headed -n 2 --reruns 1 --env=qa`}</Code>
        </Card>
        <Card title="Wrapper script">
          <Code>{`python run_tests.py --suite ui --browser firefox --headed
python run_tests.py --suite api --env qa
python run_tests.py --markers "api and smoke" --parallel auto --reruns 1 --allure-open`}</Code>
        </Card>
      </>
    ),
  },
  {
    id: "reports",
    title: "Reports & artifacts",
    render: () => (
      <>
        <h2>Step 8 – Open the reports</h2>
        <Card title="Every run gets a unique folder (never overwritten)">
          <div className="tree">{`reports/
└── 2026-09-06/
    └── execution_14-09-18/
        ├── allure-results/        ├── ui/screenshots|videos|traces|logs/
        ├── allure-report/         ├── api/requests|responses|logs/
        ├── junit/junit.xml        ├── e2e/   framework/   logs/
        ├── execution.json         └── execution_summary.html`}</div>
        </Card>
        <Card title="Allure">
          <Code>{`allure generate reports/2026-09-06/execution_14-09-18/allure-results -o reports/2026-09-06/execution_14-09-18/allure-report --clean
allure open reports/2026-09-06/execution_14-09-18/allure-report

# newest run in one line (bash)
allure serve "$(ls -td reports/*/execution_* | head -1)/allure-results"`}</Code>
          <p>Each test shows Feature / Story / Severity / Steps, environment / browser / device labels, screenshots, video, trace, test.log and every masked API request/response.</p>
        </Card>
        <Card title="Traces">
          <Code>{`playwright show-trace reports/2026-09-06/execution_14-09-18/ui/traces/<file>.zip`}</Code>
        </Card>
        <Card title="Summary, JUnit, history">
          <p>
            Open <code>execution_summary.html</code> for ID, date, env, browser, device, totals per layer and
            failures. <code>junit/junit.xml</code> feeds CI. <code>reports/execution_history.csv</code> keeps one row per run.
          </p>
        </Card>
        <Card title="Retention">
          <Code>{`python scripts/cleanup_reports.py --dry-run
python scripts/cleanup_reports.py --days 30 --executions 50 --force`}</Code>
        </Card>
      </>
    ),
  },
  {
    id: "safety",
    title: "Safety & secrets",
    render: () => (
      <>
        <h2>Step 9 – Stay safe</h2>
        <Card title="Classify every test">
          <Code lang="python">{`@pytest.mark.read_only        # only reads
@pytest.mark.data_creating    # creates records
@pytest.mark.data_modifying   # changes records
@pytest.mark.destructive      # deletes / irreversible`}</Code>
          <p>
            <code>utils/security/safety_guard.py</code> skips tests the environment forbids. On <b>prod</b>,
            non-read-only tests are blocked unless <code>prod.yaml</code> allows it <i>and</i>{" "}
            <code>ALLOW_PROD_WRITES=true</code> is set.
          </p>
        </Card>
        <Card title="Secrets">
          <ul>
            <li>Only in <code>.env</code> (git-ignored). <code>.env.example</code> has placeholders.</li>
            <li>Automatic masking of password, token, authorization, cookie, api_key, client_secret, access_token, refresh_token, JWTs – in logs, artifacts, Allure and URLs.</li>
            <li>Page Objects log passwords as <code>*****</code>.</li>
            <li>Never bypass CAPTCHA, WAF, bot protection, rate limits or authorization.</li>
          </ul>
        </Card>
      </>
    ),
  },
  {
    id: "ci",
    title: "CI/CD",
    render: () => (
      <>
        <h2>Step 10 – Run it in CI</h2>
        <table>
          <tbody>
            <tr><th>GitHub Actions</th><td><code>.github/workflows/automation.yml</code> – matrix per suite/browser, JUnit publishing, artifacts, merged Allure + Pages history</td></tr>
            <tr><th>Jenkins</th><td><code>ci/Jenkinsfile</code> – parameters, credentials binding, JUnit, Allure plugin, HTML summary</td></tr>
            <tr><th>Azure DevOps</th><td><code>ci/azure-pipelines.yml</code> – PublishTestResults, pipeline artifacts, Allure CLI</td></tr>
          </tbody>
        </table>
        <Card title="Every pipeline">
          <div className="tree">{`Install dependencies → Install Playwright browsers → Run tests
→ Allure results → JUnit XML → Publish artifacts → Publish reports`}</div>
          <p>Provide credentials as CI secrets – never in the repository.</p>
        </Card>
      </>
    ),
  },
  {
    id: "checklist",
    title: "Checklist",
    render: () => <Checklist />,
  },
];

/* -------------------------------------------------------------- checklist */

const CHECKS = [
  "Python 3.11+ installed and virtual environment activated",
  "pip install -r requirements.txt succeeded",
  "playwright install succeeded",
  ".env created from .env.example",
  "python sandbox_app/server.py is running",
  "pytest tests/framework is green",
  "pytest tests/api is green (httpbin tests may skip offline)",
  "pytest tests/ui is green",
  "pytest tests/e2e is green",
  "pytest --device=\"Pixel 7\" tests/ui/content works",
  "Opened execution_summary.html",
  "Generated and opened an Allure report",
  "Recorded a flow with playwright codegen",
  "Discovered an API with DevTools → scripts/discover_api.py",
  "Replaced the first <PLACEHOLDER> endpoint in config/environments/qa.yaml",
];

function Checklist() {
  const [done, setDone] = useState<Record<string, boolean>>(() => {
    try {
      return JSON.parse(localStorage.getItem("cc-checklist") || "{}");
    } catch {
      return {};
    }
  });
  useEffect(() => localStorage.setItem("cc-checklist", JSON.stringify(done)), [done]);
  const count = CHECKS.filter((c) => done[c]).length;
  return (
    <>
      <h2>Your progress: {count} / {CHECKS.length}</h2>
      <Card title="Getting-started checklist">
        <div className="checklist">
          {CHECKS.map((c) => (
            <label key={c}>
              <input type="checkbox" checked={!!done[c]} onChange={(e) => setDone({ ...done, [c]: e.target.checked })} />
              {c}
            </label>
          ))}
        </div>
      </Card>
      {count === CHECKS.length && (
        <Note ok>
          🎉 You are set up. Next: add your first real Page Object and API client – the framework is designed so the
          next 100 tests need no redesign.
        </Note>
      )}
      <Card title="Where to go next">
        <ul>
          <li><code>README.md</code> – full command reference</li>
          <li><code>docs/codegen_to_pom.md</code> – Codegen → Page Object worked example</li>
          <li><code>docs/api_discovery.md</code> – DevTools → cURL → test</li>
          <li><code>docs/troubleshooting.md</code> – common problems</li>
        </ul>
      </Card>
    </>
  );
}

/* -------------------------------------------------------------------- app */

export default function App() {
  const [index, setIndex] = useState(() => {
    const hash = window.location.hash.replace("#", "");
    const found = steps.findIndex((s) => s.id === hash);
    return found >= 0 ? found : 0;
  });
  const [os, setOs] = useState<OS>(() => {
    const ua = navigator.userAgent;
    if (/Windows/i.test(ua)) return "windows";
    if (/Mac/i.test(ua)) return "mac";
    return "linux";
  });
  const ctx = useMemo(() => ({ os, setOs }), [os]);
  const step = steps[index];

  useEffect(() => {
    window.location.hash = step.id;
    window.scrollTo({ top: 0 });
  }, [step.id]);

  return (
    <>
      <header>
        <h1>Coca-Cola Automation Framework – Getting Started</h1>
        <p>Python · Playwright · Pytest · Allure — UI, API and API + UI end-to-end</p>
      </header>
      <div className="layout">
        <nav>
          {steps.map((s, i) => (
            <button key={s.id} className={i === index ? "active" : i < index ? "done" : ""} onClick={() => setIndex(i)}>
              <span className="num">{i + 1}</span>
              {s.title}
            </button>
          ))}
        </nav>
        <main>
          {step.render(ctx)}
          <div className="footer-nav">
            <button disabled={index === 0} onClick={() => setIndex(index - 1)}>← Previous</button>
            <button disabled={index === steps.length - 1} onClick={() => setIndex(index + 1)}>Next →</button>
          </div>
        </main>
      </div>
    </>
  );
}
