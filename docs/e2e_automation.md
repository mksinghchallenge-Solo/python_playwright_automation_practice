# API + UI end-to-end guide

## Patterns

```text
API → UI          API creates/updates user → UI login → open profile → verify API data
UI → API          UI edits profile → API GET profile → verify backend
Full flow         API setup → UI action → API validation → cleanup
```

Implemented in `tests/e2e/api_to_ui`, `tests/e2e/ui_to_api`, `tests/e2e/full_flows`.

## Building blocks

* `api_created_user` fixture – creates a unique user via API, deletes it on teardown (API cleanup).
* `e2e_actors` fixture – bundles the user, an authenticated `ProfileClient` and the UI pages;
  `e2e_actors.ui_login()` logs in **through the UI**.

## Rules

1. **API tokens and browser sessions are not interchangeable.** The framework
   never injects an API token into the browser. If the real application
   supports sharing (e.g. a cookie the API also accepts), add an explicit,
   documented helper – don't assume it.
2. Setup via API (fast), verification via the layer the business flow demands,
   cleanup via API when an authorized cleanup endpoint exists; otherwise UI cleanup.
3. E2E tests may have ordered steps *inside one test*; never make test B depend on test A.
4. Use unique data (`TestDataFactory`) so parallel workers never collide.
