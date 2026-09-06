# Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `playwright._impl._errors.Error: Executable doesn't exist` | Run `playwright install` (Linux: `playwright install --with-deps`). If your network blocks the Playwright CDN, set `PLAYWRIGHT_DOWNLOAD_HOST` to a mirror or `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to a local Chromium. |
| Video recording fails with `ffmpeg ... doesn't exist` | `playwright install ffmpeg` |
| `SKIPPED ... Real API base URL not configured` | Expected: `config/environments/<env>.yaml` still has `<REAL_API_BASE_URL>`. Use `--env=local` with the practice app, or replace the placeholder. |
| `SKIPPED [SAFETY] ...` | The test's safety marker is not allowed in that environment (prod blocks writes). |
| `API credentials missing` | Set `API_USER_EMAIL` / `API_USER_PASSWORD` in `.env`. |
| Cookie banner intercepts clicks | Call `open_and_prepare()` or `cookie_banner.accept_if_present()`; on the real site check the OneTrust id in `ui/components/cookie_banner.py`. |
| `strict mode violation` | Locator matched multiple elements – add `.first`, a role name, or scope to a container. |
| Test hangs then times out | Locator never appears: run with `--headed --slowmo=300` or open the trace `playwright show-trace <zip>`. |
| Slow tests (~4 s each) | A `name="..."` string used where a regex was intended, causing the banner probe to wait for its timeout. Use `re.compile`. |
| `allure: command not found` | Install Allure CLI (README §1) or use `allure serve` via `npx allure-commandline serve`. |
| Parallel runs write to different folders | Only happens when `EXECUTION_DIR` is set from a previous shell – `unset EXECUTION_DIR`. |
| Practice app port in use | `python sandbox_app/server.py 8790` and set `UI_BASE_URL`/`API_BASE_URL=http://127.0.0.1:8790`. |
| Windows path issues in artifact names | Names are sanitised by `safe_name()`; keep test ids short. |
| `--browser=chrome` fails: channel not found | `playwright install chrome` (uses the installed branded browser). |

## Debug toolbox

```bash
pytest tests/ui/auth -k login --headed --slowmo=500 --trace-mode=always -x
playwright show-trace reports/<date>/execution_<time>/ui/traces/<file>.zip
PWDEBUG=1 pytest tests/ui/auth/test_login_ui.py::TestLoginUi::test_login_success   # Playwright Inspector
LOG_LEVEL=DEBUG pytest tests/api -x                                                # full request/response logs
```
