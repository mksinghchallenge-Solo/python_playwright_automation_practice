"""API tests - boundary values for profile update (data-driven from YAML)."""

import allure
import pytest

from api.clients.profile_client import ProfileClient
from api.validators.response_validator import ResponseValidator
from utils.data.data_reader import DataReader
from utils.data.test_data_factory import TestDataFactory

pytestmark = [pytest.mark.api, pytest.mark.profile, pytest.mark.boundary, pytest.mark.data_modifying]
CASES = DataReader.parametrize_cases("api/boundary_cases.yaml", key="first_name")


@allure.feature("Profile API")
@allure.story("Boundary values")
class TestProfileBoundary:
    @allure.title("first_name boundary: {case[id]}")
    @pytest.mark.regression
    @pytest.mark.parametrize("case", CASES, ids=DataReader.case_ids(CASES))
    def test_first_name_boundary(self, profile_client: ProfileClient, case: dict) -> None:
        original = profile_client.get_profile().json().get("first_name", "")
        value = case.get("value", TestDataFactory.string_of_length(case.get("value_length", 1)))
        try:
            response = profile_client.update_profile({"first_name": value})
            ResponseValidator(response).status_in(case["expected_status"])
            if response.status_code == 200:
                ResponseValidator(profile_client.get_profile()).field_equals("first_name", value)
        finally:
            profile_client.update_profile({"first_name": original})
