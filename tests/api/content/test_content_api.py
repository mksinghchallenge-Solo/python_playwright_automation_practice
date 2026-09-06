"""API tests - public content endpoint (read-only, unauthenticated)."""

import allure
import pytest

from api.clients.content_client import ContentClient
from api.validators.response_validator import ResponseValidator
from api.validators.schema_validator import SchemaValidator
from utils.api.api_helpers import assert_response_time

pytestmark = [pytest.mark.api, pytest.mark.content, pytest.mark.read_only]


@allure.feature("Content API")
@allure.story("List content")
class TestContentApi:
    @allure.title("Content list returns items with caching headers")
    @pytest.mark.smoke
    def test_list_content(self, content_client: ContentClient) -> None:
        response = content_client.list_content()
        (
            ResponseValidator(response)
            .status(200)
            .content_type("application/json")
            .cache_control_present()
            .list_not_empty("items")
        )
        SchemaValidator.validate_response(response, "api/content_list_schema.json")

    @allure.title("Content endpoint meets response-time threshold")
    @pytest.mark.performance
    def test_content_response_time(self, content_client: ContentClient) -> None:
        response = content_client.list_content()
        assert_response_time(response, max_ms=2000)
