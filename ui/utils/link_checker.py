"""
Broken-link checker.

Collects anchors from a page (via the Page Object), normalises + de-duplicates
them, classifies internal/external, checks HTTP status with ``requests``
(HEAD, falling back to GET) and writes a JSON + CSV report to the execution
folder.

The framework does NOT depend on this module - it is an optional utility used
by tests marked ``@pytest.mark.links``.
"""

from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass

import requests

from utils.artifacts.artifact_manager import get_artifact_manager
from utils.common.file_utils import write_csv
from utils.common.helpers import is_same_domain, normalize_url
from utils.logging.logger import get_logger
from utils.reporting.allure_manager import attach_json

log = get_logger("LinkChecker")

SKIP_PREFIXES = ("mailto:", "tel:", "javascript:", "sms:", "#", "data:")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; coca-cola-automation-link-checker/1.0)"}


@dataclass
class LinkResult:
    url: str
    scope: str  # internal | external
    status: int | None
    ok: bool
    error: str = ""


class LinkChecker:
    """Validate a set of links and produce a report."""

    def __init__(self, base_url: str, timeout: float = 10.0, workers: int = 8, check_external: bool = True) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.workers = workers
        self.check_external = check_external

    # ---------------------------------------------------------- collection
    def prepare(self, hrefs: Iterable[str]) -> list[tuple[str, str]]:
        """Normalise, de-duplicate and classify links -> [(url, scope)]."""
        seen: set[str] = set()
        prepared: list[tuple[str, str]] = []
        for href in hrefs:
            if not href or href.lower().startswith(SKIP_PREFIXES) or not href.startswith("http"):
                continue
            url = normalize_url(href)
            if url in seen:
                continue
            seen.add(url)
            scope = "internal" if is_same_domain(url, self.base_url) else "external"
            if scope == "external" and not self.check_external:
                continue
            prepared.append((url, scope))
        log.info("Prepared %d unique link(s) for checking", len(prepared))
        return prepared

    # ---------------------------------------------------------- checking
    def check_one(self, url: str, scope: str) -> LinkResult:
        try:
            response = requests.head(url, allow_redirects=True, timeout=self.timeout, headers=HEADERS)
            if response.status_code in (403, 405, 501) or response.status_code >= 400:
                response = requests.get(url, allow_redirects=True, timeout=self.timeout, headers=HEADERS, stream=True)
            ok = response.status_code < 400
            return LinkResult(url, scope, response.status_code, ok)
        except requests.RequestException as exc:
            return LinkResult(url, scope, None, False, f"{exc.__class__.__name__}: {exc}")

    def check(self, hrefs: Iterable[str], report_name: str = "broken_links") -> list[LinkResult]:
        prepared = self.prepare(hrefs)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            results = list(pool.map(lambda item: self.check_one(*item), prepared))
        broken = [r for r in results if not r.ok]
        log.info("Link check complete: %d checked, %d broken", len(results), len(broken))
        for result in broken:
            log.warning("BROKEN LINK | %s | %s | %s", result.scope, result.status, result.url)
        self._save(results, report_name)
        return results

    def _save(self, results: list[LinkResult], report_name: str) -> None:
        artifacts = get_artifact_manager()
        rows = [asdict(r) for r in results]
        artifacts.write_json(
            artifacts.execution.path("ui", "links", artifacts.build_name(report_name, "json")), rows, mask=False
        )
        write_csv(artifacts.execution.path("ui", "links", artifacts.build_name(report_name, "csv")), rows)
        attach_json(report_name, {"broken": [r for r in rows if not r["ok"]], "total": len(rows)}, mask=False)

    @staticmethod
    def broken(results: list[LinkResult]) -> list[LinkResult]:
        return [r for r in results if not r.ok]
