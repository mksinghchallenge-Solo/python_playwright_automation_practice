"""
Secret masking utilities.

Every log line, API request/response dump and Allure attachment passes
through :func:`mask_text` / :func:`mask_data` so credentials never reach disk.

Two strategies are combined:

1. **Key-based masking** - dictionary keys (case-insensitive) such as
   ``password``, ``token``, ``authorization`` are replaced entirely.
2. **Pattern-based masking** - free text is scanned for ``Bearer xxx``,
   ``password=xxx``, JWT-like strings, and long API-key-like tokens.
"""

from __future__ import annotations

import re
from typing import Any

MASK = "*****"

# Keys whose values must always be masked (matched case-insensitively and
# also as substrings, so "x-api-key" and "refreshToken" are caught).
SENSITIVE_KEYS: tuple[str, ...] = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "authorization",
    "auth",
    "cookie",
    "set-cookie",
    "api_key",
    "apikey",
    "api-key",
    "client_secret",
    "access_token",
    "refresh_token",
    "id_token",
    "session",
    "credential",
    "private_key",
    "x-csrf-token",
    "x-xsrf-token",
)

# Keys that contain a sensitive substring but are NOT secrets.
SAFE_KEY_EXCEPTIONS: tuple[str, ...] = (
    "author",  # contains "auth"
    "authors",
    "authority",
    "tokenizer",
    "token_type",
    "session_timeout",
    "auth_required",
    "auth_type",
    "authentication",  # inventory field describing the auth *type*
)

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Authorization: Bearer <token>   /  Basic <base64>
    (re.compile(r"(?i)(bearer|basic)\s+[A-Za-z0-9\-._~+/=]{8,}"), r"\1 " + MASK),
    # password=xxx, token: xxx, api_key="xxx" in free text / query strings.
    # The negative look-ahead keeps "Authorization: Bearer <masked>" readable.
    (
        re.compile(
            r"(?i)((?:password|passwd|pwd|token|secret|api[_-]?key|client[_-]?secret|"
            r"access[_-]?token|refresh[_-]?token|authorization|cookie)\s*[:=]\s*[\"']?)"
            r"(?!bearer\b|basic\b|\*{5})([^\s\"'&,;}]+)"
        ),
        r"\1" + MASK,
    ),
    # JSON: "password": "xxx"
    (
        re.compile(
            r"(?i)(\"(?:password|passwd|pwd|token|secret|api[_-]?key|client[_-]?secret|"
            r"access[_-]?token|refresh[_-]?token|authorization|cookie)\"\s*:\s*\")([^\"]*)(\")"
        ),
        r"\1" + MASK + r"\3",
    ),
    # JWT-like strings: aaaa.bbbb.cccc
    (re.compile(r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+"), MASK + ".jwt"),
)


def is_sensitive_key(key: Any) -> bool:
    """Return True when a dictionary key should have its value masked."""
    if not isinstance(key, str):
        return False
    lowered = key.lower().replace("-", "_")
    if lowered in {k.replace("-", "_") for k in SAFE_KEY_EXCEPTIONS}:
        return False
    return any(marker.replace("-", "_") in lowered for marker in SENSITIVE_KEYS)


def mask_text(text: str, enabled: bool = True) -> str:
    """Mask secrets in a free-text string."""
    if not enabled or not text:
        return text
    result = text
    for pattern, replacement in _PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def mask_data(data: Any, enabled: bool = True) -> Any:
    """Recursively mask secrets in dicts / lists / strings.

    Returns a *new* structure; the input is never mutated.
    """
    if not enabled:
        return data
    if isinstance(data, dict):
        return {
            key: (MASK if is_sensitive_key(key) and value not in (None, "") else mask_data(value, enabled))
            for key, value in data.items()
        }
    if isinstance(data, (list, tuple)):
        return type(data)(mask_data(item, enabled) for item in data)
    if isinstance(data, str):
        return mask_text(data, enabled)
    return data


def mask_headers(headers: Any, enabled: bool = True) -> dict[str, str]:
    """Convenience wrapper for HTTP header mappings."""
    return dict(mask_data(dict(headers or {}), enabled))


def mask_url(url: str, enabled: bool = True) -> str:
    """Mask secrets carried in query strings (``?token=...``)."""
    return mask_text(url, enabled)
