"""
Dynamic test-data factory.

Generates *predictable* unique data so parallel tests never collide and
created records are easy to find (and clean up) afterwards.

All generated identifiers share a recognisable prefix (``autotest``) plus a
timestamp and a short UUID, e.g.::

    autotest_20260906_023541_a1b2c3d4@example.com
"""

from __future__ import annotations

import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from faker import Faker

from utils.common.helpers import random_string

TEST_DATA_PREFIX = os.getenv("TEST_DATA_PREFIX", "autotest")
TEST_EMAIL_DOMAIN = os.getenv("TEST_EMAIL_DOMAIN", "example.com")

_faker = Faker()


@dataclass
class TestUser:
    """A generated user - never a real person and never a real credential."""

    __test__ = False  # tell pytest this is data, not a test class

    email: str
    password: str
    first_name: str
    last_name: str
    birth_date: str
    zip_code: str
    tag: str = field(default_factory=lambda: TEST_DATA_PREFIX)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def as_public_dict(self) -> dict[str, Any]:
        """Dict without the password - safe for logs and Allure."""
        data = asdict(self)
        data.pop("password", None)
        return data


class TestDataFactory:
    """Factory for unique, traceable test data."""

    __test__ = False

    @staticmethod
    def timestamp() -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def unique_id(length: int = 8) -> str:
        return uuid.uuid4().hex[:length]

    @classmethod
    def unique_token(cls, label: str = "") -> str:
        """``autotest_<label>_<timestamp>_<uuid>``"""
        parts = [TEST_DATA_PREFIX]
        if label:
            parts.append(label)
        parts.extend([cls.timestamp(), cls.unique_id()])
        return "_".join(parts)

    @classmethod
    def unique_email(cls, label: str = "") -> str:
        return f"{cls.unique_token(label)}@{TEST_EMAIL_DOMAIN}"

    @staticmethod
    def strong_password(length: int = 14) -> str:
        """Generated password satisfying typical complexity rules."""
        core = random_string(length - 4)
        return f"Aa1!{core}"

    @classmethod
    def user(cls, label: str = "user", **overrides: Any) -> TestUser:
        data: dict[str, Any] = {
            "email": cls.unique_email(label),
            "password": cls.strong_password(),
            "first_name": _faker.first_name(),
            "last_name": _faker.last_name(),
            "birth_date": _faker.date_of_birth(minimum_age=21, maximum_age=60).isoformat(),
            "zip_code": _faker.postcode(),
        }
        data.update(overrides)
        return TestUser(**data)

    @classmethod
    def profile_update_payload(cls, **overrides: Any) -> dict[str, Any]:
        payload = {
            "first_name": f"Upd{_faker.first_name()}",
            "last_name": f"Upd{_faker.last_name()}",
            "zip_code": _faker.postcode(),
        }
        payload.update(overrides)
        return payload

    @staticmethod
    def string_of_length(length: int, char: str = "a") -> str:
        return char * length

    @staticmethod
    def special_characters() -> str:
        return "!@#$%^&*()_+-=[]{}|;':\",./<>?`~ éñ中文🙂"
