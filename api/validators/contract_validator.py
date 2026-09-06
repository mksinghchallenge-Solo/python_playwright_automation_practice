"""
Contract validator.

A *contract* bundles everything a consumer relies on for one endpoint:
status code, required headers, JSON schema and optional response-time SLA.
Contracts live in ``schemas/api/contracts/*.yaml``::

    endpoint: profile
    method: GET
    expected_status: 200
    required_headers: [Content-Type]
    content_type: application/json
    schema: api/profile_schema.json
    max_response_time_ms: 2000

Use :meth:`ContractValidator.validate` in ``tests/api/contract``.
"""

from __future__ import annotations

from typing import Any

from api.models.api_response import ApiResponse
from api.validators.response_validator import ResponseValidator
from api.validators.schema_validator import SchemaValidator
from utils.data.data_reader import SCHEMAS_DIR, DataReader
from utils.logging.logger import get_logger

log = get_logger("ContractValidator")


class ContractValidator:
    """Validates a response against a YAML contract definition."""

    @staticmethod
    def load(contract_path: str) -> dict[str, Any]:
        """Load ``schemas/<contract_path>`` (e.g. ``api/contracts/profile_contract.yaml``)."""
        contract = DataReader.load(contract_path, base_dir=SCHEMAS_DIR)
        if not isinstance(contract, dict):
            raise ValueError(f"Contract must be a mapping: {contract_path}")
        return contract

    @classmethod
    def validate(cls, response: ApiResponse, contract: dict[str, Any] | str) -> None:
        """Validate ``response`` against a contract dict or ``schemas/<path>``."""
        if isinstance(contract, str):
            contract = cls.load(contract)
        name = contract.get("name") or f"{contract.get('method', '?')} {contract.get('endpoint', '?')}"
        log.info("CONTRACT | validating %s", name)

        validator = ResponseValidator(response)
        if "expected_status" in contract:
            validator.status(int(contract["expected_status"]))
        for header in contract.get("required_headers", []) or []:
            validator.header_present(header)
        if contract.get("content_type"):
            validator.content_type(str(contract["content_type"]))
        if contract.get("max_response_time_ms"):
            validator.response_time_below(float(contract["max_response_time_ms"]))
        if contract.get("required_fields"):
            validator.fields_present(list(contract["required_fields"]))
        if contract.get("schema"):
            SchemaValidator.validate_response(response, str(contract["schema"]))
        log.info("CONTRACT OK | %s", name)
