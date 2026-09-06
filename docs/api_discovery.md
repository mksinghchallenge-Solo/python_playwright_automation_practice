# API discovery with Chrome DevTools

> Only automate APIs you are **authorized** to test. Never bypass
> authentication, CAPTCHA, WAF, bot protection, rate limits or authorization.
> Do not invent endpoints – if you have not observed and been authorized to
> use it, keep the `<PLACEHOLDER>`.

## Workflow

```text
Open website → F12 (DevTools) → Network tab → filter Fetch/XHR → tick "Preserve log"
→ perform the UI action (login, open profile, save profile)
→ click the request → inspect:
      Headers: URL, Method, Status, Request/Response headers, Authorization, Cookies,
               X-Request-Id / X-Correlation-Id
      Payload: query string, path params, JSON/form body
      Response: JSON shape (→ JSON Schema)
→ right-click request → Copy → Copy as cURL (bash)
→ python scripts/discover_api.py --curl "<paste>" --name get_profile
→ replace placeholder in config/environments/<env>.yaml
→ add client method + test + schema + inventory entry
```

## What to write down for every endpoint

| Item | Where it goes |
|---|---|
| URL + method | `config/environments/<env>.yaml → api.endpoints.<name>` and `docs/api_inventory.yaml` |
| Auth type (bearer / cookie / API key) | inventory `authentication`; choose `TokenManager` / `ApiKeyProvider` |
| Required headers | client `default_headers` or per-call `headers=` |
| Request body shape | `schemas/api/<name>_request_schema.json` (optional) |
| Response body shape | `schemas/api/<name>_schema.json` |
| Correlation id header name | `ResponseValidator.correlation_id_present(candidates=...)` |
| Side effects | safety marker: read_only / data_creating / data_modifying / destructive |

## From cURL to test – example

```bash
python scripts/discover_api.py --name get_profile --curl "curl 'https://<host>/api/v1/users/me' \
  -H 'accept: application/json' -H 'authorization: Bearer eyJ...' --compressed"
```

Output: masked parsed request, a client method draft, a pytest draft and an
inventory entry draft (`--write` saves them under `discovered/<name>/`).

1. `config/environments/qa.yaml`: `profile: /api/v1/users/me`, `base_url: https://<host>`
2. `api/clients/profile_client.py`: method already exists (`get_profile`) – adjust if the path/params differ.
3. `schemas/api/profile_schema.json`: adjust to the observed response.
4. `pytest tests/api/profile --env=qa` – the auto-skip lifts as soon as placeholders are replaced.
5. `docs/api_inventory.yaml`: set `test_status: automated`; run `scripts/generate_api_inventory.py`.

## Placeholders currently in use

`<REAL_API_BASE_URL>`, `<AUTH_ENDPOINT>`, `<REFRESH_ENDPOINT>`, `<LOGOUT_ENDPOINT>`,
`<SIGNUP_ENDPOINT>`, `<PROFILE_ENDPOINT>`, `<UPDATE_PROFILE_ENDPOINT>`,
`<DELETE_USER_ENDPOINT>`, `<CONTENT_ENDPOINT>` – all in
`config/environments/{qa,staging,prod}.yaml` and `docs/api_inventory.yaml`.
