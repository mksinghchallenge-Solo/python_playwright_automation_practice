# API Coverage

_Generated 2026-09-06T14:12:08 from `docs/api_inventory.yaml`_

| Metric | Value |
|---|---|
| Total endpoints | 8 |
| Automated | 5 |
| Partially automated | 2 |
| Not automated | 1 |
| Still placeholders (`<...>`) | 8 |
| Coverage | **62.5%** |

| Name | Method | Endpoint | Auth | Safety | Risk | Status | Test file |
|---|---|---|---|---|---|---|---|
| login | POST | `<AUTH_ENDPOINT>` | none (credentials in body) | read_only | high | automated | tests/api/auth/test_login_api.py |
| refresh | POST | `<REFRESH_ENDPOINT>` | refresh token in body | read_only | medium | partial | api/clients/auth_client.py (TokenManager) |
| logout | POST | `<LOGOUT_ENDPOINT>` | bearer | read_only | low | not_automated | - |
| signup | POST | `<SIGNUP_ENDPOINT>` | none | data_creating | high | automated | fixtures/api_fixtures.py (api_created_user) + tests/e2e/** |
| get_profile | GET | `<PROFILE_ENDPOINT>` | bearer | read_only | medium | automated | tests/api/profile/test_profile_api.py |
| update_profile | PUT | `<UPDATE_PROFILE_ENDPOINT>` | bearer | data_modifying | high | automated | tests/api/profile/test_profile_api.py |
| delete_user | DELETE | `<DELETE_USER_ENDPOINT>` | bearer | destructive | high | partial | fixtures/api_fixtures.py (cleanup) |
| list_content | GET | `<CONTENT_ENDPOINT>` | none | read_only | low | automated | tests/api/content/test_content_api.py |

## Dependency chains

### profile_update_flow
_Login -> token -> read profile -> update -> re-read -> verify_

```text
1. login
   ↓
2. get_profile
   ↓
3. update_profile
   ↓
4. get_profile
```

### user_lifecycle_flow
_Signup -> login as new user -> profile -> delete (cleanup)_

```text
1. signup
   ↓
2. login
   ↓
3. get_profile
   ↓
4. delete_user
```

### token_refresh_flow
_Login -> wait for expiry -> refresh -> continue_

```text
1. login
   ↓
2. refresh
   ↓
3. get_profile
```
