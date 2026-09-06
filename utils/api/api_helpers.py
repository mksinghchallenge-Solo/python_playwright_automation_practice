"""
API helper utilities.

* :func:`curl_to_request` - parse a DevTools "Copy as cURL (bash)" string into
  a dict you can paste into a client method (used by scripts/discover_api.py).
* :func:`measure` - simple timing decorator for ad-hoc measurements.
* :func:`assert_response_time` - one-liner SLA check using config thresholds.
"""

from __future__ import annotations

import shlex
import time
from collections.abc import Callable
from functools import wraps
from typing import Any
from urllib.parse import parse_qsl, urlparse

from api.models.api_response import ApiResponse
from utils.config.config_reader import get_config
from utils.logging.logger import get_logger

log = get_logger("ApiHelpers")


def curl_to_request(curl_command: str) -> dict[str, Any]:
    """Convert a ``curl ...`` command into ``{method, url, headers, params, data}``."""
    tokens = shlex.split(curl_command.replace("\\\n", " "))
    if not tokens or tokens[0] != "curl":
        raise ValueError("Command must start with 'curl'")

    method = "GET"
    url = ""
    headers: dict[str, str] = {}
    data: str | None = None
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in ("-X", "--request"):
            method = tokens[index + 1].upper()
            index += 2
        elif token in ("-H", "--header"):
            name, _, value = tokens[index + 1].partition(":")
            headers[name.strip()] = value.strip()
            index += 2
        elif token in ("-d", "--data", "--data-raw", "--data-binary", "--data-urlencode"):
            data = tokens[index + 1]
            if method == "GET":
                method = "POST"
            index += 2
        elif token in ("-b", "--cookie"):
            headers["Cookie"] = tokens[index + 1]
            index += 2
        elif token.startswith("-"):
            index += 1  # ignore flags such as --compressed
        else:
            url = token
            index += 1

    parsed = urlparse(url)
    return {
        "method": method,
        "url": f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
        "params": dict(parse_qsl(parsed.query)),
        "headers": headers,
        "data": data,
    }


def measure(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator logging how long a function took (ms)."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            log.info("%s took %.0f ms", func.__name__, (time.perf_counter() - start) * 1000)

    return wrapper


def assert_response_time(response: ApiResponse, max_ms: float | None = None) -> None:
    """Fail when the response is slower than ``max_ms`` (default from config)."""
    threshold = max_ms if max_ms is not None else get_config().api_fail_ms
    log.info(
        "PERF | %s | Response time: %.0f ms (threshold %.0f ms)", response.describe(), response.elapsed_ms, threshold
    )
    assert response.elapsed_ms <= threshold, f"{response.describe()} exceeded response-time threshold {threshold} ms"
