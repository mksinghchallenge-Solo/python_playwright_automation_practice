# CI/CD

All pipelines follow the same stages:

```text
Install dependencies → Install Playwright browsers → (start practice app if ENV=local)
→ Run tests (-n, --reruns) → Allure results → JUnit XML → Publish artifacts → Publish reports
```

| Provider | File | Notes |
|---|---|---|
| GitHub Actions | `.github/workflows/automation.yml` | matrix (framework/api/ui×3 browsers/e2e), `dorny/test-reporter` for JUnit, artifacts per job, merged Allure report + optional GitHub Pages history |
| Jenkins | `ci/Jenkinsfile` | parameters, `credentials()` binding, `junit`, Allure plugin, `publishHTML` summary, `archiveArtifacts` |
| Azure DevOps | `ci/azure-pipelines.yml` | `PublishTestResults@2`, `PublishPipelineArtifact@1`, Allure via CLI |

## Secrets

Never commit `.env`. Provide `API_USER_EMAIL`, `API_USER_PASSWORD`,
`UI_USER_EMAIL`, `UI_USER_PASSWORD` as CI secrets; the pipeline writes them
into `.env` at runtime (or exports them – env vars win over `.env`).

## Execution folder in CI

The newest folder is `ls -td reports/*/execution_* | head -1`; publish that
whole directory as the build artifact – it contains Allure results, JUnit,
screenshots, videos, traces, logs and the HTML summary.

## Recommended CI settings

* `-n 2` on standard runners, `--reruns 1 --reruns-delay 2`.
* Exclude optional suites by default: `-m "not accessibility and not links"`.
* Nightly: full regression on chromium + firefox + webkit + one mobile device.
* Prod: only `-m read_only --env=prod`; the safety guard enforces it anyway.
