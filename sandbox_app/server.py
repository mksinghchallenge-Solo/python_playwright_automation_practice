"""
Local PRACTICE application (pure standard library - no extra dependencies).

WHY THIS EXISTS
---------------
The real Coca-Cola account APIs are not public/known, and the framework must
never invent them. This tiny app gives you a *safe, local* target that has
the same shape as a typical account flow so you can:

* run the API, UI and API+UI E2E samples end-to-end on your laptop/CI
* learn the framework before pointing it at authorized endpoints
* practise the Codegen -> Page Object workflow

It is intentionally simple and NOT production code.

Run it::

    python sandbox_app/server.py            # http://127.0.0.1:8765
    ENV=local pytest                        # run the suite against it

Pages : /            /login     /signup     /profile     /profile/edit
API   : POST /api/auth/login      -> {access_token, refresh_token, expires_in}
        POST /api/auth/refresh
        POST /api/auth/logout
        POST /api/users           (signup)
        GET  /api/users/me        (Bearer)
        PUT  /api/users/me        (Bearer)
        DELETE /api/users/{id}    (Bearer)
        GET  /api/content/pages
"""

from __future__ import annotations

import json
import secrets
import sys
import threading
import time
import uuid
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

HOST = "0.0.0.0"
PORT = 8765
TOKEN_TTL_SECONDS = 3600

# ---------------------------------------------------------------- storage
_lock = threading.Lock()
USERS: dict[str, dict[str, Any]] = {}  # email -> user
TOKENS: dict[str, dict[str, Any]] = {}  # access token -> {email, expires_at}
REFRESH_TOKENS: dict[str, str] = {}  # refresh token -> email
SESSIONS: dict[str, str] = {}  # UI session cookie -> email
CONTENT = [
    {"id": "coke-original", "title": "Coca-Cola Original Taste", "type": "product"},
    {"id": "coke-zero", "title": "Coca-Cola Zero Sugar", "type": "product"},
    {"id": "sustainability", "title": "Sustainability", "type": "page"},
]


def seed_default_user() -> None:
    """A known demo user (documented in test_data/ui/users.yaml, local section)."""
    USERS["demo.user@example.com"] = {
        "id": "usr_demo",
        "email": "demo.user@example.com",
        "password": "Demo@12345",
        "first_name": "Demo",
        "last_name": "User",
        "zip_code": "30301",
    }


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in user.items() if k != "password"}


def issue_tokens(email: str) -> dict[str, Any]:
    access = secrets.token_urlsafe(32)
    refresh = secrets.token_urlsafe(32)
    TOKENS[access] = {"email": email, "expires_at": time.time() + TOKEN_TTL_SECONDS}
    REFRESH_TOKENS[refresh] = email
    return {"access_token": access, "refresh_token": refresh, "token_type": "Bearer", "expires_in": TOKEN_TTL_SECONDS}


# ------------------------------------------------------------------- html
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | Practice App</title>
<style>
 body{{font-family:Arial,sans-serif;margin:0;background:#fafafa;color:#222}}
 header{{background:#d50000;color:#fff;padding:14px 24px;display:flex;gap:24px;align-items:center}}
 header a{{color:#fff;text-decoration:none;font-weight:bold}}
 main{{max-width:640px;margin:32px auto;background:#fff;padding:24px;border-radius:8px;box-shadow:0 1px 4px #0002}}
 label{{display:block;margin:12px 0 4px}} input{{padding:8px;width:100%;box-sizing:border-box}}
 button{{margin-top:16px;padding:10px 18px;background:#d50000;color:#fff;border:0;border-radius:4px;cursor:pointer}}
 .error{{color:#b00020}} .success{{color:#0a7a2f}}
 #cookie-banner{{position:fixed;bottom:0;left:0;right:0;background:#222;color:#fff;padding:16px;display:flex;justify-content:space-between;align-items:center}}
 #cookie-banner button{{margin:0 6px}}
 footer{{text-align:center;padding:24px;color:#595959}}
</style></head><body>
<header role="banner"><a href="/" aria-label="Practice App home">Practice App</a>
 <nav aria-label="Main"><a href="/">Home</a> &nbsp; <a href="/login">Sign in</a> &nbsp; <a href="/signup">Create account</a> &nbsp; <a href="/profile">Profile</a></nav>
 {user_area}
</header>
<main>{body}</main>
<footer role="contentinfo">Practice application for the Coca-Cola automation framework. Not affiliated with The Coca-Cola Company.</footer>
{banner}
<script>
 const banner=document.getElementById('cookie-banner');
 if(banner){{
   if(localStorage.getItem('cookie-consent')) banner.remove();
   document.querySelectorAll('#cookie-banner button').forEach(b=>b.addEventListener('click',()=>{{localStorage.setItem('cookie-consent',b.dataset.choice);banner.remove();}}));
 }}
</script>
</body></html>"""

BANNER = """<div id="cookie-banner" role="dialog" aria-label="Cookie consent"><span>We use cookies to improve your experience.</span>
<span><button data-choice="reject">Reject All</button><button data-choice="accept">Accept All Cookies</button></span></div>"""


def render(title: str, body: str, email: str | None = None, banner: bool = True) -> bytes:
    user_area = (
        f'<span style="margin-left:auto">Signed in as <strong data-testid="current-user">{email}</strong> &nbsp; <a href="/logout">Sign out</a></span>'
        if email
        else ""
    )
    return PAGE.format(title=title, body=body, user_area=user_area, banner=BANNER if banner else "").encode()


HOME_BODY = """<h1>Welcome to the Practice App</h1>
<p>Use this app to try the automation framework locally.</p>
<section aria-label="Featured products"><h2>Products</h2><ul>
<li><a href="/products/coke-original">Coca-Cola Original Taste</a></li>
<li><a href="/products/coke-zero">Coca-Cola Zero Sugar</a></li>
<li><a href="https://www.coca-cola.com/us/en" target="_blank" rel="noopener">Official Coca-Cola site (new tab)</a></li>
</ul></section>"""

LOGIN_BODY = """<h1>Sign in</h1>{message}
<form method="post" action="/login">
<label for="email">Email address</label><input id="email" name="email" type="email" placeholder="you@example.com" required>
<label for="password">Password</label><input id="password" name="password" type="password" placeholder="Password" required>
<button type="submit">Sign in</button></form>
<p>No account? <a href="/signup">Create account</a></p>"""

SIGNUP_BODY = """<h1>Create account</h1>{message}
<form method="post" action="/signup">
<label for="first_name">First name</label><input id="first_name" name="first_name" required>
<label for="last_name">Last name</label><input id="last_name" name="last_name" required>
<label for="email">Email address</label><input id="email" name="email" type="email" required>
<label for="password">Password</label><input id="password" name="password" type="password" minlength="8" required>
<label for="zip_code">ZIP code</label><input id="zip_code" name="zip_code" required>
<button type="submit">Create account</button></form>"""

PROFILE_BODY = """<h1>My profile</h1>
<dl>
<dt>First name</dt><dd data-testid="profile-first-name">{first_name}</dd>
<dt>Last name</dt><dd data-testid="profile-last-name">{last_name}</dd>
<dt>Email</dt><dd data-testid="profile-email">{email}</dd>
<dt>ZIP code</dt><dd data-testid="profile-zip">{zip_code}</dd>
</dl><a href="/profile/edit" role="button">Edit profile</a>"""

EDIT_BODY = """<h1>Edit profile</h1>{message}
<form method="post" action="/profile/edit">
<label for="first_name">First name</label><input id="first_name" name="first_name" value="{first_name}" required>
<label for="last_name">Last name</label><input id="last_name" name="last_name" value="{last_name}" required>
<label for="zip_code">ZIP code</label><input id="zip_code" name="zip_code" value="{zip_code}" required>
<button type="submit">Save changes</button></form>"""


# ---------------------------------------------------------------- handler
class Handler(BaseHTTPRequestHandler):
    server_version = "PracticeApp/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stdout.write(f"{self.address_string()} - {fmt % args}\n")

    # ---- helpers
    def _send(self, status: int, body: bytes, content_type: str, extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Request-Id", uuid.uuid4().hex)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, payload: Any, extra: dict[str, str] | None = None) -> None:
        self._send(status, json.dumps(payload).encode(), "application/json; charset=utf-8", extra)

    def _html(self, status: int, body: bytes, extra: dict[str, str] | None = None) -> None:
        self._send(status, body, "text/html; charset=utf-8", extra)

    def _redirect(self, location: str, extra: dict[str, str] | None = None) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(length) if length else b""

    def _form(self) -> dict[str, str]:
        return {k: v[0] for k, v in parse_qs(self._body().decode()).items()}

    def _json_body(self) -> tuple[Any, str | None]:
        raw = self._body()
        if not raw:
            return None, "empty body"
        try:
            return json.loads(raw), None
        except json.JSONDecodeError as exc:
            return None, f"malformed JSON: {exc.msg}"

    def _session_email(self) -> str | None:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        sid = cookie.get("session")
        return SESSIONS.get(sid.value) if sid else None

    def _bearer_email(self) -> tuple[str | None, str | None]:
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None, "missing bearer token"
        token = auth.split(" ", 1)[1].strip()
        entry = TOKENS.get(token)
        if not entry:
            return None, "invalid token"
        if entry["expires_at"] < time.time():
            return None, "expired token"
        return entry["email"], None

    # ---- routing
    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        email = self._session_email()
        if path == "/":
            self._html(200, render("Home", HOME_BODY, email))
        elif path == "/login":
            self._html(200, render("Sign in", LOGIN_BODY.format(message=""), email))
        elif path == "/signup":
            self._html(200, render("Create account", SIGNUP_BODY.format(message=""), email))
        elif path == "/logout":
            self._redirect("/", {"Set-Cookie": "session=; Path=/; Max-Age=0"})
        elif path == "/profile":
            if not email:
                self._redirect("/login")
                return
            self._html(200, render("My profile", PROFILE_BODY.format(**USERS[email]), email))
        elif path == "/profile/edit":
            if not email:
                self._redirect("/login")
                return
            self._html(200, render("Edit profile", EDIT_BODY.format(message="", **USERS[email]), email))
        elif path.startswith("/products/"):
            item = next((c for c in CONTENT if c["id"] == path.rsplit("/", 1)[-1]), None)
            if item:
                self._html(200, render(item["title"], f"<h1>{item['title']}</h1><p>Product page.</p>", email))
            else:
                self._html(404, render("Not found", "<h1>Page not found</h1>", email))
        elif path == "/broken-link-demo":
            self._html(404, render("Not found", "<h1>Page not found</h1>", email))
        elif path == "/api/users/me":
            user_email, error = self._bearer_email()
            if error:
                self._json(401, {"error": error})
                return
            self._json(200, public_user(USERS[user_email]))
        elif path == "/api/content/pages":
            self._json(200, {"items": CONTENT, "total": len(CONTENT)}, {"Cache-Control": "public, max-age=60"})
        elif path == "/api/health":
            self._json(200, {"status": "ok", "users": len(USERS)})
        else:
            self._json(404, {"error": "not found", "path": path})

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/login":
            form = self._form()
            user = USERS.get(form.get("email", ""))
            if not user or user["password"] != form.get("password"):
                self._html(
                    401,
                    render(
                        "Sign in",
                        LOGIN_BODY.format(message='<p class="error" role="alert">Invalid email or password.</p>'),
                    ),
                )
                return
            sid = secrets.token_urlsafe(16)
            with _lock:
                SESSIONS[sid] = user["email"]
            self._redirect("/profile", {"Set-Cookie": f"session={sid}; Path=/; HttpOnly"})
        elif path == "/signup":
            form = self._form()
            if form.get("email") in USERS:
                self._html(
                    409,
                    render(
                        "Create account",
                        SIGNUP_BODY.format(
                            message='<p class="error" role="alert">An account with this email already exists.</p>'
                        ),
                    ),
                )
                return
            with _lock:
                USERS[form["email"]] = {"id": f"usr_{uuid.uuid4().hex[:8]}", **form}
            sid = secrets.token_urlsafe(16)
            SESSIONS[sid] = form["email"]
            self._redirect("/profile", {"Set-Cookie": f"session={sid}; Path=/; HttpOnly"})
        elif path == "/profile/edit":
            email = self._session_email()
            if not email:
                self._redirect("/login")
                return
            form = self._form()
            with _lock:
                USERS[email].update({k: form[k] for k in ("first_name", "last_name", "zip_code") if k in form})
            self._redirect("/profile")
        elif path == "/api/auth/login":
            payload, error = self._json_body()
            if error:
                self._json(400, {"error": error})
                return
            if not isinstance(payload, dict):
                self._json(400, {"error": "body must be an object"})
                return
            missing = [f for f in ("email", "password") if not payload.get(f)]
            if missing:
                self._json(422, {"error": "missing fields", "fields": missing})
                return
            user = USERS.get(str(payload["email"]))
            if not user or user["password"] != payload["password"]:
                self._json(401, {"error": "invalid credentials"})
                return
            with _lock:
                tokens = issue_tokens(user["email"])
            self._json(200, tokens)
        elif path == "/api/auth/refresh":
            payload, error = self._json_body()
            email = REFRESH_TOKENS.get((payload or {}).get("refresh_token", "")) if not error else None
            if not email:
                self._json(401, {"error": "invalid refresh token"})
                return
            self._json(200, issue_tokens(email))
        elif path == "/api/auth/logout":
            auth = self.headers.get("Authorization", "")
            TOKENS.pop(auth.replace("Bearer ", "").strip(), None)
            self._send(204, b"", "application/json")
        elif path == "/api/users":
            payload, error = self._json_body()
            if error or not isinstance(payload, dict):
                self._json(400, {"error": error or "body must be an object"})
                return
            required = ("email", "password", "first_name", "last_name")
            missing = [f for f in required if not payload.get(f)]
            if missing:
                self._json(422, {"error": "missing fields", "fields": missing})
                return
            if len(str(payload["password"])) < 8:
                self._json(422, {"error": "password too short", "fields": ["password"]})
                return
            if payload["email"] in USERS:
                self._json(409, {"error": "email already registered"})
                return
            user = {"id": f"usr_{uuid.uuid4().hex[:8]}", "zip_code": "", **payload}
            with _lock:
                USERS[user["email"]] = user
            self._json(201, public_user(user), {"Location": f"/api/users/{user['id']}"})
        else:
            self._json(404, {"error": "not found", "path": path})

    def do_PUT(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/users/me":
            email, error = self._bearer_email()
            if error:
                self._json(401, {"error": error})
                return
            payload, body_error = self._json_body()
            if body_error or not isinstance(payload, dict):
                self._json(400, {"error": body_error or "body must be an object"})
                return
            allowed = {"first_name", "last_name", "zip_code"}
            unknown = sorted(set(payload) - allowed)
            if unknown:
                self._json(422, {"error": "unknown fields", "fields": unknown})
                return
            with _lock:
                USERS[email].update({k: str(v) for k, v in payload.items()})
            self._json(200, public_user(USERS[email]))
        else:
            self._json(405 if path.startswith("/api/") else 404, {"error": "method not allowed"})

    def do_PATCH(self) -> None:  # noqa: N802
        self.do_PUT()

    def do_DELETE(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api/users/"):
            email, error = self._bearer_email()
            if error:
                self._json(401, {"error": error})
                return
            user_id = path.rsplit("/", 1)[-1]
            target = next((u for u in USERS.values() if u["id"] == user_id), None)
            if not target:
                self._json(404, {"error": "user not found"})
                return
            if target["email"] != email:
                self._json(403, {"error": "cannot delete another user"})
                return
            with _lock:
                USERS.pop(target["email"], None)
            self._send(204, b"", "application/json")
        else:
            self._json(404, {"error": "not found"})


def run(host: str = HOST, port: int = PORT) -> None:
    seed_default_user()
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Practice app listening on http://{host}:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run(port=port_arg)
