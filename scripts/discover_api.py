#!/usr/bin/env python
"""
API discovery helper.

Turns a "Copy as cURL (bash)" string from Chrome DevTools into:
  1. a parsed summary (method, URL, params, headers with secrets masked)
  2. a ready-to-edit API client method
  3. a ready-to-edit pytest test
  4. a draft inventory entry for docs/api_inventory.yaml

It NEVER sends the request. Discovery = documenting what the browser did;
you decide whether you are authorized to automate it.

Usage:
    python scripts/discover_api.py --curl "curl 'https://…' -H 'accept: application/json' …"
    python scripts/discover_api.py --file captured_request.curl --name get_profile
    python scripts/discover_api.py --file captured.curl --name get_profile --write   # writes drafts to discovered/
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utils.api.api_helpers import curl_to_request  # noqa: E402
from utils.logging.masking import mask_data  # noqa: E402

DISCOVERED_DIR = PROJECT_ROOT / "discovered"

CLIENT_TEMPLATE = '''
    def {name}(self{params_signature}) -> ApiResponse:
        """{method} {path}  (discovered via DevTools - verify authorization before use)."""
        return self.{verb}(
            self.environment.endpoint("{name}"),{params_kw}{json_kw}
            artifact_name="{name}",
        )
'''

TEST_TEMPLATE = '''"""Auto-drafted from a DevTools cURL capture. Review before committing."""

import allure
import pytest

from api.validators.response_validator import ResponseValidator

pytestmark = [pytest.mark.api, pytest.mark.read_only]


@allure.feature("{feature}")
class Test{class_name}:
    @allure.title("{method} {path} returns 200")
    def test_{name}(self, {client_fixture}):
        response = {client_fixture}.{name}({call_args})
        (ResponseValidator(response)
         .status(200)
         .content_type("application/json"))
        # TODO: add field/schema assertions, e.g.
        # .field_present("id")
        # SchemaValidator.validate_response(response, "api/{name}_schema.json")
'''

INVENTORY_TEMPLATE = """  - name: {name}
    endpoint: "{path}"
    method: {method}
    purpose: TODO
    authentication: {auth}
    request_schema: null
    response_schema: null
    test_status: not_automated
    test_file: tests/api/<area>/test_{name}_api.py
    environment: [qa]
    safety: {safety}
    risk: medium
    depends_on: []
"""


def draft(parsed: dict, name: str) -> dict[str, str]:
    method = parsed["method"]
    path = urlparse(parsed["url"]).path
    verb = method.lower()
    has_body = parsed.get("data") is not None and method in ("POST", "PUT", "PATCH")
    has_params = bool(parsed.get("params"))
    auth = "bearer" if "authorization" in {k.lower() for k in parsed["headers"]} else "none"
    safety = (
        "read_only"
        if method in ("GET", "HEAD", "OPTIONS")
        else ("destructive" if method == "DELETE" else "data_modifying")
    )

    client = CLIENT_TEMPLATE.format(
        name=name,
        method=method,
        path=path,
        verb=verb,
        params_signature=(", **query: Any" if has_params else "") + (", payload: dict[str, Any]" if has_body else ""),
        params_kw="\n            params=query or None," if has_params else "",
        json_kw="\n            json=payload," if has_body else "",
    )
    test = TEST_TEMPLATE.format(
        feature=name.replace("_", " ").title(),
        class_name="".join(p.title() for p in name.split("_")),
        method=method,
        path=path,
        name=name,
        client_fixture="content_client",
        call_args=("payload={}" if has_body else ""),
    )
    inventory = INVENTORY_TEMPLATE.format(name=name, path=path, method=method, auth=auth, safety=safety)
    return {"client_method": client, "test": test, "inventory": inventory}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--curl", help="cURL command string")
    source.add_argument("--file", help="file containing the cURL command")
    parser.add_argument("--name", default=None, help="logical endpoint name, e.g. get_profile")
    parser.add_argument("--write", action="store_true", help="write drafts into discovered/<name>/")
    args = parser.parse_args()

    curl = args.curl or Path(args.file).read_text(encoding="utf-8")
    parsed = curl_to_request(curl)
    name = args.name or re.sub(
        r"[^a-z0-9]+", "_", (parsed["method"] + "_" + urlparse(parsed["url"]).path).lower()
    ).strip("_")

    print("=" * 70)
    print("PARSED REQUEST (secrets masked - never paste real tokens into code)")
    print("=" * 70)
    print(json.dumps(mask_data(parsed), indent=2))
    drafts = draft(parsed, name)
    for title, body in (
        ("CLIENT METHOD DRAFT", drafts["client_method"]),
        ("TEST DRAFT", drafts["test"]),
        ("INVENTORY ENTRY DRAFT", drafts["inventory"]),
    ):
        print("\n" + "=" * 70 + f"\n{title}\n" + "=" * 70)
        print(body)
    print("NEXT STEPS")
    print(f"  1. Add the path to config/environments/<env>.yaml -> api.endpoints.{name}")
    print("  2. Paste the client method into the relevant api/clients/*_client.py")
    print(f"  3. Save the test as tests/api/<area>/test_{name}_api.py and add assertions")
    print("  4. Add the inventory entry to docs/api_inventory.yaml, then run scripts/generate_api_inventory.py")

    if args.write:
        target = DISCOVERED_DIR / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "request.json").write_text(json.dumps(mask_data(parsed), indent=2), encoding="utf-8")
        (target / "client_method.py.txt").write_text(drafts["client_method"], encoding="utf-8")
        (target / f"test_{name}_api.py").write_text(drafts["test"], encoding="utf-8")
        (target / "inventory_entry.yaml").write_text(drafts["inventory"], encoding="utf-8")
        print(f"\nDrafts written to {target.relative_to(PROJECT_ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
