"""
Test safety classification and production protection.

Every test is classified with one of the markers::

    @pytest.mark.read_only        # only reads data
    @pytest.mark.data_creating    # creates new records
    @pytest.mark.data_modifying   # changes existing records
    @pytest.mark.destructive      # deletes records / irreversible

Unmarked tests are treated as READ_ONLY *for reporting*, but a warning is
logged so you remember to classify them.

Before each test runs, :func:`check_test_allowed` compares the level with
the active environment's ``safety`` section. On production all non-read-only
tests are skipped unless BOTH the YAML flag AND ``ALLOW_PROD_WRITES=true``
are present - an intentional double lock.
"""

from __future__ import annotations

import os
from enum import Enum

import pytest

from utils.config.environment_manager import Environment
from utils.logging.logger import get_logger

log = get_logger("SafetyGuard")


class SafetyLevel(str, Enum):  # noqa: UP042 - keep str mixin for readability on 3.10
    READ_ONLY = "read_only"
    DATA_CREATING = "data_creating"
    DATA_MODIFYING = "data_modifying"
    DESTRUCTIVE = "destructive"


SAFETY_MARKERS: tuple[str, ...] = tuple(level.value for level in SafetyLevel)


def resolve_safety_level(item: pytest.Item) -> SafetyLevel:
    """Return the highest-risk safety marker present on a test item."""
    present = [level for level in SafetyLevel if item.get_closest_marker(level.value)]
    if not present:
        log.debug("Test %s has no safety marker; treating as READ_ONLY", item.nodeid)
        return SafetyLevel.READ_ONLY
    # Enum declaration order == increasing risk.
    ordered = list(SafetyLevel)
    return max(present, key=ordered.index)


def is_allowed(level: SafetyLevel, environment: Environment) -> tuple[bool, str]:
    """Return ``(allowed, reason)`` for a level in an environment."""
    if level is SafetyLevel.READ_ONLY:
        return True, ""

    if not environment.allows(level.value):
        return False, (
            f"{level.value} tests are disabled for environment '{environment.name}' "
            f"(see safety.allow_{level.value} in {environment.file_path.name})"
        )

    if environment.is_production:
        prod_override = os.getenv("ALLOW_PROD_WRITES", "false").lower() in {"1", "true", "yes"}
        if not prod_override:
            return False, (
                f"{level.value} tests are blocked on PRODUCTION. "
                "Set ALLOW_PROD_WRITES=true only if you are explicitly authorized."
            )
    return True, ""


def check_test_allowed(item: pytest.Item, environment: Environment) -> None:
    """Skip the test when its safety level is not permitted. Called from conftest."""
    level = resolve_safety_level(item)
    allowed, reason = is_allowed(level, environment)
    if not allowed:
        log.warning("SAFETY BLOCK | %s | %s", item.nodeid, reason)
        pytest.skip(f"[SAFETY] {reason}")
