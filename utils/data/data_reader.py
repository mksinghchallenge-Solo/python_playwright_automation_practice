"""
Test-data reader.

Loads files from ``test_data/`` in JSON, YAML or CSV format and exposes them
as plain Python structures. Also provides :func:`load_parametrize_cases` for
pytest data-driven tests.

Layout::

    test_data/
    ├── api/      <- payloads, credentials templates (no secrets!)
    ├── ui/       <- UI users, navigation expectations
    └── shared/   <- data used by both layers

Example::

    from utils.data.data_reader import DataReader
    users = DataReader.load("ui/users.yaml")
    cases = DataReader.parametrize_cases("api/login_negative_cases.csv")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.common.file_utils import read_csv, read_json, read_yaml
from utils.config.config_reader import PROJECT_ROOT
from utils.logging.logger import get_logger

TEST_DATA_DIR = PROJECT_ROOT / "test_data"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"

log = get_logger("DataReader")


class DataFileError(Exception):
    """Raised when a test-data file is missing or malformed."""


class DataReader:
    """Reads JSON / YAML / CSV test data with a single call."""

    _cache: dict[Path, Any] = {}

    @classmethod
    def resolve(cls, relative_path: str, base_dir: Path = TEST_DATA_DIR) -> Path:
        path = (base_dir / relative_path).resolve()
        if not path.exists():
            raise DataFileError(f"Test data file not found: {path}")
        return path

    @classmethod
    def load(cls, relative_path: str, base_dir: Path = TEST_DATA_DIR, use_cache: bool = True) -> Any:
        """Load a data file. Format is chosen from the extension."""
        path = cls.resolve(relative_path, base_dir)
        if use_cache and path in cls._cache:
            return cls._cache[path]

        suffix = path.suffix.lower()
        try:
            if suffix == ".json":
                data = read_json(path)
            elif suffix in {".yaml", ".yml"}:
                data = read_yaml(path)
            elif suffix == ".csv":
                data = read_csv(path)
            else:
                raise DataFileError(f"Unsupported test data format '{suffix}': {path}")
        except (ValueError, OSError) as exc:
            raise DataFileError(f"Failed to read test data {path}: {exc}") from exc

        log.debug("Loaded test data: %s", path.relative_to(PROJECT_ROOT))
        if use_cache:
            cls._cache[path] = data
        return data

    @classmethod
    def load_schema(cls, relative_path: str) -> dict[str, Any]:
        """Load a JSON Schema from ``schemas/``."""
        schema = cls.load(relative_path, base_dir=SCHEMAS_DIR)
        if not isinstance(schema, dict):
            raise DataFileError(f"Schema must be a JSON object: {relative_path}")
        return schema

    @classmethod
    def parametrize_cases(cls, relative_path: str, key: str | None = None) -> list[Any]:
        """Return a list usable with ``@pytest.mark.parametrize``.

        * CSV -> list of row dicts
        * JSON/YAML list -> the list itself
        * JSON/YAML dict -> ``data[key]`` (or the dict's values)
        """
        data = cls.load(relative_path)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if key:
                if key not in data:
                    raise DataFileError(f"Key '{key}' not found in {relative_path}")
                return list(data[key])
            return list(data.values())
        raise DataFileError(f"Cannot build parametrize cases from {relative_path}")

    @classmethod
    def case_ids(cls, cases: list[Any], id_field: str = "id") -> list[str]:
        """Human-readable pytest ids for parametrized cases."""
        ids: list[str] = []
        for index, case in enumerate(cases):
            if isinstance(case, dict) and id_field in case:
                ids.append(str(case[id_field]))
            else:
                ids.append(f"case_{index}")
        return ids

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()
