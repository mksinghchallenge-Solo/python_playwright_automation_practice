"""Small generic helpers shared across layers."""

from __future__ import annotations

import random
import string
import uuid
from collections.abc import Iterable
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse


def random_string(length: int = 8, alphabet: str = string.ascii_lowercase + string.digits) -> str:
    return "".join(random.choice(alphabet) for _ in range(length))


def short_uuid(length: int = 8) -> str:
    return uuid.uuid4().hex[:length]


def join_url(base: str, path: str) -> str:
    """Join base URL and path without losing the base path segment."""
    if path.startswith(("http://", "https://")):
        return path
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def normalize_url(url: str) -> str:
    """Strip fragments and trailing slashes so duplicate links compare equal."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", parsed.query, ""))


def is_same_domain(url: str, base_url: str) -> bool:
    return urlparse(url).netloc.lower().removeprefix("www.") == urlparse(base_url).netloc.lower().removeprefix("www.")


def deep_get(data: Any, dotted_path: str, default: Any = None) -> Any:
    """``deep_get({"a": {"b": [1, 2]}}, "a.b.1") -> 2``"""
    node = data
    for part in dotted_path.split("."):
        if isinstance(node, dict):
            if part not in node:
                return default
            node = node[part]
        elif isinstance(node, list) and part.isdigit():
            index = int(part)
            if index >= len(node):
                return default
            node = node[index]
        else:
            return default
    return node


def chunked(items: Iterable[Any], size: int) -> list[list[Any]]:
    items = list(items)
    return [items[i : i + size] for i in range(0, len(items), size)]
