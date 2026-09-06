# UI automation guide

## Page Object Model

```text
BasePage
   ├── HomePage        (cookie_banner, navigation, popups, headings, links)
   ├── LoginPage       (login(email, password), expect_error)
   ├── SignupPage      (sign_up(user))
   ├── ProfilePage     (profile_data(), expect_first_name, sign_out)
   └── EditProfilePage (update(first_name=..., zip_code=...))
Components: CookieBanner, Navigation, Modal, PopupHandler
```

Page Objects expose *business actions* and `expect_*` assertions; tests never
see raw selectors.

## Locator priority

1. `get_by_role` 2. `get_by_label` 3. `get_by_placeholder` 4. `get_by_test_id`
5. `get_by_text` 6. CSS 7. XPath (only when unavoidable).

Use `re.compile("sign in", re.I)` for names – a plain string in `name=` is a
*substring* match, not a regex.

## Waiting

Never `time.sleep()`. Use `expect(locator).to_be_visible()`, Playwright
auto-waiting on actions, and `BasePage.is_visible(locator, timeout_ms)` only for
optional elements (banners, popups).

## Cookie banner / popups / dialogs / new tabs

* `home_page.open_and_prepare()` = open + accept cookies + dismiss overlays + auto-accept native dialogs.
* `Modal(page, ctx).close()`, `PopupHandler.dismiss_overlays_if_present()`.
* `BasePage.click_and_wait_for_new_tab(locator, "description")` returns the new `Page`.

## Screenshots, video, trace

Configured per policy (`always | retain-on-failure | never`) in `config.yaml` /
`.env` / CLI. Manual screenshots: `page_object.screenshot("meaningful_name")`.

## Browsers & devices

`--browser=chromium|chrome|msedge|firefox|webkit`, `--device="Pixel 7"`.
WebKit ≈ Safari engine; mobile = emulation (see README section 11).

## Real site vs practice app

The Page Objects use generic role/label locators that work on the local
practice app today. For the real Coca-Cola account pages, record with Codegen,
then adjust the locators inside the Page Object only (tests stay unchanged) –
see `codegen_to_pom.md`.
