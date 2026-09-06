"""
JSON Schema validator.

Schemas live under ``schemas/api/*.json`` and follow JSON Schema draft
2020-12. Validation errors list *every* problem (not just the first) with a
JSON-pointer style path so you can find the field instantly.

Example::

    from api.validators.schema_validator import SchemaValidator
    SchemaValidator.validate_response(response, "api/profile_schema.json")
"""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from api.models.api_response import ApiResponse
from utils.data.data_reader import DataReader
from utils.logging.logger import get_logger
from utils.reporting.allure_manager import attach_json, attach_text

log = get_logger("SchemaValidator")


class SchemaValidationError(AssertionError):
    """Raised when a payload does not match its JSON Schema."""


class SchemaValidator:
    """Validates payloads or responses against JSON Schemas."""

    @staticmethod
    def errors(payload: Any, schema: dict[str, Any]) -> list[str]:
        """Return a list of readable error strings (empty == valid)."""
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        messages: list[str] = []
        for error in sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path)):
            path = "/".join(str(p) for p in error.absolute_path) or "<root>"
            messages.append(f"{path}: {error.message}")
        return messages

    @classmethod
    def validate(cls, payload: Any, schema: dict[str, Any], schema_name: str = "schema") -> None:
        problems = cls.errors(payload, schema)
        if problems:
            report = "\n".join(f"  - {p}" for p in problems)
            attach_text(f"Schema violations ({schema_name})", report)
            attach_json(f"Payload validated against {schema_name}", payload)
            log.error("SCHEMA FAILED | %s | %d problem(s)", schema_name, len(problems))
            raise SchemaValidationError(f"Payload violates {schema_name} ({len(problems)} problem(s)):\n{report}")
        log.info("SCHEMA OK | %s", schema_name)

    @classmethod
    def validate_file(cls, payload: Any, schema_path: str) -> None:
        """Validate against ``schemas/<schema_path>``."""
        cls.validate(payload, DataReader.load_schema(schema_path), schema_name=schema_path)

    @classmethod
    def validate_response(cls, response: ApiResponse, schema_path: str) -> None:
        try:
            body = response.json()
        except ValueError as exc:
            raise SchemaValidationError(f"Cannot validate schema: {exc}\n{response.failure_report()}") from exc
        try:
            cls.validate_file(body, schema_path)
        except SchemaValidationError as exc:
            raise SchemaValidationError(f"{exc}\n--- {response.describe()} ---\n{response.failure_report()}") from None
