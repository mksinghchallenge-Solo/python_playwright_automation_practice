"""
Example tests against a SAFE PUBLIC echo API (httpbin.org).

Purpose: prove verbs, form/multipart bodies, Basic/Bearer auth and masking
work in *your* network before real Coca-Cola endpoints are known.
Requires internet access; skipped automatically when httpbin is unreachable.
NOT a Coca-Cola API - delete when no longer needed.
"""

import allure
import pytest

from api.clients.auth_client import StaticTokenProvider
from api.clients.base_client import ApiClientError
from api.clients.example_client import ExampleClient
from api.validators.response_validator import ResponseValidator
from api.validators.schema_validator import SchemaValidator

pytestmark = [pytest.mark.api, pytest.mark.read_only, pytest.mark.regression]


@pytest.fixture(scope="module")
def httpbin(example_client: ExampleClient) -> ExampleClient:
    try:
        if example_client.status(200).status_code != 200:
            pytest.skip("httpbin.org not healthy")
    except ApiClientError as exc:
        pytest.skip(f"httpbin.org unreachable from this network: {exc}")
    return example_client


@allure.feature("Example public API (httpbin)")
class TestExamplePublicApi:
    def test_get_with_query(self, httpbin: ExampleClient) -> None:
        response = httpbin.echo_get(page=1, q="coke")
        ResponseValidator(response).status(200).field_equals("args.page", "1").field_equals("args.q", "coke")
        SchemaValidator.validate_response(response, "api/httpbin_echo_schema.json")

    @pytest.mark.parametrize("verb", ["post", "put", "patch"])
    def test_json_body_verbs(self, httpbin: ExampleClient, verb: str) -> None:
        response = getattr(httpbin, f"echo_{verb}")({"brand": "Coca-Cola", "zero": True})
        ResponseValidator(response).status(200).field_equals("json.brand", "Coca-Cola").field_equals("json.zero", True)

    def test_form_and_multipart(self, httpbin: ExampleClient) -> None:
        ResponseValidator(httpbin.form_post({"a": "1"})).status(200).field_equals("form.a", "1")
        ResponseValidator(httpbin.multipart_post({"file": ("hello.txt", b"hello", "text/plain")})).status(
            200
        ).field_present("files.file")

    def test_bearer_auth_required(self, httpbin: ExampleClient) -> None:
        ResponseValidator(httpbin.bearer()).status(401)
        httpbin.auth_provider = StaticTokenProvider("demo-token-123")
        try:
            ResponseValidator(httpbin.bearer()).status(200).field_equals("authenticated", True)
        finally:
            httpbin.auth_provider = None

    def test_basic_auth(self, httpbin: ExampleClient) -> None:
        ResponseValidator(httpbin.basic_auth("user", "passwd")).status(200).field_equals("authenticated", True)

    @pytest.mark.parametrize("code", [201, 204, 400, 401, 403, 404, 409, 422, 429, 500])
    def test_status_codes(self, httpbin: ExampleClient, code: int) -> None:
        ResponseValidator(httpbin.status(code)).status(code)
