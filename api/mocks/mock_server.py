"""
Lightweight local mock API server for *API-layer* tests.

When a real endpoint is unavailable/unstable you can still exercise clients,
validators and schemas against a local HTTP server that serves canned
responses. The server runs in a background thread on a free port so
parallel workers never collide.

Mocked tests MUST be marked ``@pytest.mark.mocked`` - they live in
``tests/api/mocked`` and are excluded from real integration runs by
``pytest -m "api and not mocked"``.

Example::

    with MockApiServer() as server:
        server.add_route("GET", "/api/v1/users/me", 200, {"id": "u1", "email": "a@b.c"})
        client = BaseAPIClient(server.base_url)
        client.get("/api/v1/users/me").status_code == 200
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from utils.logging.logger import get_logger

log = get_logger("MockApiServer")


@dataclass
class MockRoute:
    method: str
    path: str
    status: int
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict)
    handler: Callable[[dict[str, Any]], tuple[int, Any]] | None = None  # dynamic responses


@dataclass
class RecordedRequest:
    method: str
    path: str
    query: str
    headers: dict[str, str]
    body: Any


class MockApiServer:
    """Thread-based mock HTTP server with route registration + request recording."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self.routes: dict[tuple[str, str], MockRoute] = {}
        self.requests: list[RecordedRequest] = []
        self._lock = threading.Lock()
        server_ref = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: Any) -> None:  # silence stdlib logging
                log.debug("mock %s", fmt % args)

            def _handle(self) -> None:
                parsed = urlparse(self.path)
                length = int(self.headers.get("Content-Length", 0) or 0)
                raw_body = self.rfile.read(length) if length else b""
                try:
                    body: Any = json.loads(raw_body) if raw_body else None
                except json.JSONDecodeError:
                    body = raw_body.decode(errors="replace")

                record = RecordedRequest(self.command, parsed.path, parsed.query, dict(self.headers), body)
                with server_ref._lock:
                    server_ref.requests.append(record)

                route = server_ref.routes.get((self.command, parsed.path))
                if route is None:
                    self._send(404, {"error": "no mock route", "method": self.command, "path": parsed.path})
                    return
                status, payload = route.status, route.body
                if route.handler is not None:
                    status, payload = route.handler(
                        {
                            "method": self.command,
                            "path": parsed.path,
                            "query": parsed.query,
                            "headers": dict(self.headers),
                            "body": body,
                        }
                    )
                self._send(status, payload, route.headers)

            def _send(self, status: int, payload: Any, extra_headers: dict[str, str] | None = None) -> None:
                data = b"" if payload is None else json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Request-Id", "mock-request-id")
                for key, value in (extra_headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                if data and self.command != "HEAD":
                    self.wfile.write(data)

            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _handle  # noqa: N815

        self._server = ThreadingHTTPServer((host, port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    # ------------------------------------------------------------ control
    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        host_text = host.decode() if isinstance(host, bytes) else str(host)
        return f"http://{host_text}:{port}"

    def start(self) -> MockApiServer:
        self._thread.start()
        log.info("Mock API server started at %s", self.base_url)
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        log.info("Mock API server stopped")

    def __enter__(self) -> MockApiServer:
        return self.start()

    def __exit__(self, *exc: Any) -> None:
        self.stop()

    # ------------------------------------------------------------- routes
    def add_route(
        self,
        method: str,
        path: str,
        status: int = 200,
        body: Any = None,
        headers: dict[str, str] | None = None,
        handler: Callable[[dict[str, Any]], tuple[int, Any]] | None = None,
    ) -> None:
        self.routes[(method.upper(), path)] = MockRoute(method.upper(), path, status, body, headers or {}, handler)

    def requests_for(self, method: str, path: str) -> list[RecordedRequest]:
        return [r for r in self.requests if r.method == method.upper() and r.path == path]

    def reset(self) -> None:
        with self._lock:
            self.requests.clear()
