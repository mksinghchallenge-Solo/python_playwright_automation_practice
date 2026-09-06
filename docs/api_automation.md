# API automation guide

## Clients

```text
BaseAPIClient            GET POST PUT PATCH DELETE HEAD OPTIONS, headers, params,
  ├── AuthClient         path params, json, form, multipart, cookies, auth provider,
  ├── UserClient         timeout, SSL, proxies, retries (safe verbs), masked logging,
  ├── ProfileClient      artifacts, Allure, response time
  ├── ContentClient
  └── ExampleClient      (httpbin echo – framework validation only)
```

Every method returns an `ApiResponse` (`status_code`, `headers`, `json()`,
`elapsed_ms`, `describe()`, `failure_report()`); HTTP errors never raise – you
assert them. Only transport failures raise `ApiClientError`.

## Authentication

```python
manager = TokenManager(AuthClient(env), email, password)   # cache + expiry + refresh
client = ProfileClient(env, auth_provider=manager)
client.get_profile()                                          # Authorization: Bearer ***** added
```

Other providers: `StaticTokenProvider("...")`, `ApiKeyProvider(key, "X-API-Key")`.
Credentials come from `.env` (`API_USER_EMAIL`, `API_USER_PASSWORD`, optional `API_STATIC_TOKEN`).

The login response shape is **assumed** (`access_token`, `refresh_token`,
`expires_in`). Adjust `TokenManager._parse_token_response` and
`schemas/api/auth_token_schema.json` to the real API.

## Validation

```python
(ResponseValidator(response)
    .status(200)                          # 200 201 204 400 401 403 404 409 422 429 500 ...
    .content_type("application/json")
    .header_present("Cache-Control").correlation_id_present().security_headers_present()
    .response_time_below(1500)
    .field_equals("email", email).field_type("id", str).field_not_null("id")
    .field_absent("password").list_not_empty("items"))
SchemaValidator.validate_response(response, "api/profile_schema.json")
ContractValidator.validate(response, "api/contracts/profile_contract.yaml")
assert_response_time(response, max_ms=2000)   # utils/api/api_helpers.py
```

## Test types & where they live

| Type | Folder | Example |
|---|---|---|
| Positive | `tests/api/auth`, `profile`, `content` | `test_login_with_valid_credentials` |
| Negative | `tests/api/negative` | wrong password, missing fields, malformed JSON, invalid token, unsupported method |
| Boundary | `tests/api/profile/test_profile_boundary_api.py` | min/max length, empty, special chars, 1000 chars |
| Contract | `tests/api/contract` | YAML contract |
| Schema | `tests/api/schema` | JSON Schema |
| Data-driven | JSON/YAML/CSV via `DataReader.parametrize_cases` | `login_negative_cases.json` |
| Mocked | `tests/api/mocked` (`-m mocked`) | `MockApiServer` |

## Dependency map

```text
Login → Token → Get Profile → Update Profile → Get Profile → Verify Updated Data
```

Machine-readable: `docs/api_dependency_map.yaml`; rendered in `docs/api_coverage.md`.

## Inventory & coverage

`docs/api_inventory.yaml` → `python scripts/generate_api_inventory.py` →
`docs/api_coverage.md` + `.json` (total / automated / partial / not automated).

## Performance basics

Every response logs `Response time: N ms`; above
`performance.api_response_time_warn_ms` a WARNING is logged;
`assert_response_time()` fails above the configured/explicit threshold.
This is a smoke-level check, not load testing.
