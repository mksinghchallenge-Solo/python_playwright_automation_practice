"""Framework self-tests: data readers, factory, API client (via mock), validators."""

import allure
import pytest

from api.clients.auth_client import StaticTokenProvider
from api.clients.base_client import ApiClientError, BaseAPIClient
from api.mocks.mock_server import MockApiServer
from api.validators.response_validator import ApiAssertionError, ResponseValidator
from api.validators.schema_validator import SchemaValidationError, SchemaValidator
from utils.api.api_helpers import curl_to_request
from utils.data.data_reader import DataFileError, DataReader
from utils.data.test_data_factory import TestDataFactory

pytestmark = [pytest.mark.framework, pytest.mark.read_only]


@allure.feature("Framework")
@allure.story("Test data")
class TestData:
    def test_yaml_json_csv_loading(self) -> None:
        assert "local_demo_user" in DataReader.load("ui/users.yaml")
        assert isinstance(DataReader.load("api/login_negative_cases.json"), list)
        rows = DataReader.load("ui/login_negative_cases.csv")
        assert rows and rows[0]["id"] == "wrong_password"

    def test_missing_file_gives_clear_error(self) -> None:
        with pytest.raises(DataFileError, match="not found"):
            DataReader.load("ui/does_not_exist.yaml")

    def test_parametrize_cases_and_ids(self) -> None:
        cases = DataReader.parametrize_cases("api/login_negative_cases.json")
        ids = DataReader.case_ids(cases)
        assert "wrong_password" in ids and len(ids) == len(cases)

    def test_schema_loading(self) -> None:
        schema = DataReader.load_schema("api/profile_schema.json")
        assert schema["title"] == "Profile"

    def test_factory_generates_unique_predictable_data(self) -> None:
        a, b = TestDataFactory.user(), TestDataFactory.user()
        assert a.email != b.email
        assert a.email.startswith("autotest_user_") and a.email.endswith("@example.com")
        assert "password" not in a.as_public_dict()
        assert len(TestDataFactory.strong_password()) >= 12


@allure.feature("Framework")
@allure.story("API client")
class TestApiClient:
    def test_all_verbs_and_auth_header(self, mock_server: MockApiServer) -> None:
        for verb in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
            mock_server.add_route(verb, "/ping", 200, {"verb": verb})
        client = BaseAPIClient(mock_server.base_url, auth_provider=StaticTokenProvider("abc123"))
        for verb in ("get", "post", "put", "patch", "delete", "head", "options"):
            response = getattr(client, verb)("/ping")
            assert response.status_code == 200, verb
        recorded = mock_server.requests_for("GET", "/ping")[0]
        assert recorded.headers["Authorization"] == "Bearer abc123"

    def test_path_params_query_and_json(self, mock_server: MockApiServer) -> None:
        mock_server.add_route(
            "POST", "/users/42/notes", 201, handler=lambda req: (201, {"echo": req["body"], "query": req["query"]})
        )
        client = BaseAPIClient(mock_server.base_url)
        response = client.post("/users/{id}/notes", path_params={"id": 42}, params={"lang": "en"}, json={"text": "hi"})
        assert response.status_code == 201
        assert response.json()["echo"] == {"text": "hi"}
        assert response.json()["query"] == "lang=en"
        assert response.elapsed_ms >= 0

    def test_transport_error_is_explicit(self) -> None:
        client = BaseAPIClient("http://127.0.0.1:9", timeout=1, max_retries=0)
        with pytest.raises(ApiClientError, match="failed after"):
            client.get("/nothing")

    def test_curl_conversion(self) -> None:
        parsed = curl_to_request(
            "curl 'https://api.example.com/v1/me?x=1' -H 'Authorization: Bearer abc' "
            "--data-raw '{\"a\":1}' --compressed"
        )
        assert parsed["method"] == "POST" and parsed["url"] == "https://api.example.com/v1/me"
        assert parsed["params"] == {"x": "1"} and parsed["data"] == '{"a":1}'


@allure.feature("Framework")
@allure.story("Validators")
class TestValidators:
    def test_response_validator_chain(self, mock_server: MockApiServer) -> None:
        mock_server.add_route("GET", "/profile", 200, {"id": "u1", "email": "a@b.co", "age": 30, "tags": ["x"]})
        response = BaseAPIClient(mock_server.base_url).get("/profile")
        (
            ResponseValidator(response)
            .status(200)
            .content_type("application/json")
            .header_present("X-Request-Id")
            .correlation_id_present()
            .field_equals("email", "a@b.co")
            .field_type("age", int)
            .field_not_null("id")
            .list_not_empty("tags")
            .field_absent("password")
            .response_time_below(5000)
        )

    def test_response_validator_failure_includes_report(self, mock_server: MockApiServer) -> None:
        mock_server.add_route("GET", "/profile", 500, {"error": "boom"})
        response = BaseAPIClient(mock_server.base_url).get("/profile")
        with pytest.raises(ApiAssertionError) as excinfo:
            ResponseValidator(response).status(200)
        assert "Expected status 200 but got 500" in str(excinfo.value)
        assert '"boom"' in str(excinfo.value)

    def test_schema_validator_lists_all_problems(self) -> None:
        schema = DataReader.load_schema("api/profile_schema.json")
        problems = SchemaValidator.errors({"id": 1, "email": "nope"}, schema)
        assert any("first_name" in p for p in problems)
        assert any("id" in p for p in problems)
        with pytest.raises(SchemaValidationError):
            SchemaValidator.validate({"id": 1}, schema, "profile")
