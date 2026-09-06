# Codegen → Page Object Model (worked example: login)

```text
Codegen → Generated script → Identify actions → Move locators to Page Object
→ Move test data to test_data/ → Move assertions into test → Add reusable methods
→ Add Allure metadata → Add logging → Final maintainable test
```

## 1. Record

```bash
playwright codegen --target python-pytest -o generated_login.py http://127.0.0.1:8765/login
# real site: playwright codegen --target python-pytest https://www.coca-cola.com/us/en
```

## 2. Generated script (typical output)

```python
import re
from playwright.sync_api import Page, expect

def test_example(page: Page) -> None:
    page.goto("http://127.0.0.1:8765/login")
    page.get_by_role("button", name="Accept All Cookies").click()
    page.get_by_label("Email address").click()
    page.get_by_label("Email address").fill("demo.user@example.com")
    page.get_by_label("Password").click()
    page.get_by_label("Password").fill("Demo@12345")
    page.get_by_role("button", name="Sign in").click()
    expect(page.get_by_test_id("current-user")).to_have_text("demo.user@example.com")
```

Problems: hardcoded URL, hardcoded password, cookie logic inline, no reuse,
no reporting, no logging.

## 3. Identify actions

| Generated line | Belongs to |
|---|---|
| `goto(".../login")` | `LoginPage.open()` (URL from environment) |
| Accept All Cookies | `CookieBanner.accept_if_present()` |
| fill email / password, click Sign in | `LoginPage.login(email, password)` |
| `expect(current-user)` | `ProfilePage.expect_signed_in_as(email)` |
| `"demo.user@example.com"`, `"Demo@12345"` | `.env` (`UI_USER_EMAIL/PASSWORD`) |

## 4. Move locators to the Page Object (`ui/pages/login_page.py`)

```python
class LoginPage(BasePage):
    PATH = "login"

    def __init__(self, page, context):
        super().__init__(page, context)
        self.cookie_banner = CookieBanner(page, context)
        self.email_input = page.get_by_label(re.compile("email", re.I)).first
        self.password_input = page.get_by_label(re.compile("^password", re.I)).first
        self.submit_button = page.get_by_role("button", name=re.compile(r"^(sign in|log in)$", re.I)).first

    def open_and_prepare(self):
        self.open(); self.cookie_banner.accept_if_present(); return self

    def login(self, email, password):
        with step(f"Login as {email}"):                     # Allure step
            self.fill(self.email_input, email, "email")     # logged
            self.fill(self.password_input, password, "password", secret=True)   # masked
            self.click(self.submit_button, "Sign in button")
```

## 5. Move test data out

`.env`: `UI_USER_EMAIL=...`, `UI_USER_PASSWORD=...` (never in code).
Negative cases: `test_data/ui/login_negative_cases.csv`.

## 6. Final test (`tests/ui/auth/test_login_ui.py`)

```python
@allure.feature("Authentication UI")
@allure.story("Login")
class TestLoginUi:
    @allure.title("Valid user can sign in and sees the profile")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_login_success(self, login_page, profile_page, ui_credentials):
        email, password = ui_credentials
        login_page.open_and_prepare()
        login_page.expect_loaded()
        login_page.login(email, password)
        profile_page.expect_loaded()
        profile_page.expect_signed_in_as(email)
        profile_page.screenshot("test_login_success")

    @pytest.mark.parametrize("case", NEGATIVE, ids=[c["id"] for c in NEGATIVE])
    def test_login_negative(self, login_page, case):
        login_page.open_and_prepare()
        login_page.login(case["email"], case["password"])
        login_page.expect_error(case["expected_error"])
```

What you gained: environment-independent URL, no secrets, one cookie handler,
reusable `login()`, Allure steps/labels/screenshot, structured masked logs,
data-driven negatives – and the next 100 tests reuse the same pieces.

## Tips

* Codegen emits exact strings (`name="Sign in"`); convert to `re.compile(..., re.I)` for resilience.
* Prefer `get_by_role` / `get_by_label` that Codegen already suggests over CSS it falls back to.
* Record on mobile too: `playwright codegen --device="iPhone 14" <url>` – if locators differ, branch inside the Page Object, not the test.
