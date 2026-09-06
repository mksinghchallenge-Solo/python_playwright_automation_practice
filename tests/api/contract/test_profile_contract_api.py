"""API tests - contract validation (status + headers + schema + SLA in one YAML)."""

import allure
import pytest

from api.clients.profile_client import ProfileClient
from api.validators.contract_validator import ContractValidator

pytestmark = [pytest.mark.api, pytest.mark.contract, pytest.mark.read_only]


@allure.feature("Contracts")
class TestProfileContract:
    @allure.title("GET profile honours its contract")
    @pytest.mark.regression
    def test_profile_contract(self, profile_client: ProfileClient) -> None:
        ContractValidator.validate(profile_client.get_profile(), "api/contracts/profile_contract.yaml")
