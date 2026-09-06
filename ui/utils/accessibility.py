"""
Accessibility checks with axe-core (via ``axe-playwright-python``).

Usage in a test marked ``@pytest.mark.accessibility``::

    from ui.utils.accessibility import AccessibilityChecker
    result = AccessibilityChecker(page, context).run(level="AA")
    assert result.violation_count == 0, result.summary()

``level`` maps to axe tags: "A" -> wcag2a, "AA" -> wcag2a + wcag2aa.
Results are saved as JSON under ``ui/`` in the execution folder and attached
to Allure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import Page

from utils.artifacts.artifact_manager import get_artifact_manager
from utils.common.runtime_context import RuntimeContext
from utils.logging.logger import get_logger
from utils.reporting.allure_manager import attach_json, step

log = get_logger("Accessibility")

LEVEL_TAGS: dict[str, list[str]] = {
    "A": ["wcag2a", "wcag21a"],
    "AA": ["wcag2a", "wcag21a", "wcag2aa", "wcag21aa"],
}


@dataclass
class AccessibilityResult:
    url: str
    level: str
    violations: list[dict[str, Any]] = field(default_factory=list)
    passes: int = 0
    incomplete: int = 0
    report_path: Path | None = None

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    def violations_by_impact(self, impacts: tuple[str, ...] = ("critical", "serious")) -> list[dict[str, Any]]:
        return [v for v in self.violations if v.get("impact") in impacts]

    def summary(self) -> str:
        lines = [
            f"Accessibility ({self.level}) for {self.url}: {self.violation_count} violation(s), "
            f"{self.passes} pass(es), {self.incomplete} incomplete"
        ]
        for violation in self.violations:
            lines.append(
                f"  - [{violation.get('impact')}] {violation.get('id')}: {violation.get('help')} "
                f"({len(violation.get('nodes', []))} node(s)) {violation.get('helpUrl')}"
            )
        return "\n".join(lines)


class AccessibilityChecker:
    """Runs axe-core against the current page."""

    def __init__(self, page: Page, context: RuntimeContext) -> None:
        self.page = page
        self.context = context

    def run(
        self, level: str = "AA", include: str | None = None, exclude: list[str] | None = None
    ) -> AccessibilityResult:
        from axe_playwright_python.sync_playwright import Axe  # imported lazily: optional feature

        tags = LEVEL_TAGS.get(level.upper())
        if tags is None:
            raise ValueError(f"Unsupported level '{level}'. Use 'A' or 'AA'.")

        with step(f"Run axe accessibility scan (WCAG {level.upper()})"):
            log.info("Running axe-core scan level=%s on %s", level, self.page.url)
            options: dict[str, Any] = {"runOnly": {"type": "tag", "values": tags}}
            axe_context: Any = None
            if include or exclude:
                axe_context = {}
                if include:
                    axe_context["include"] = [[include]]
                if exclude:
                    axe_context["exclude"] = [[selector] for selector in exclude]
            raw = Axe().run(self.page, context=axe_context, options=options).response

        result = AccessibilityResult(
            url=self.page.url,
            level=level.upper(),
            violations=list(raw.get("violations", [])),
            passes=len(raw.get("passes", [])),
            incomplete=len(raw.get("incomplete", [])),
        )
        artifacts = get_artifact_manager()
        result.report_path = artifacts.write_json(
            artifacts.execution.path(
                "ui",
                "accessibility",
                artifacts.build_name("axe", "json", self.context.browser_label, self.context.device_label),
            ),
            {
                "url": result.url,
                "level": result.level,
                "violations": result.violations,
                "passes": result.passes,
                "incomplete": result.incomplete,
            },
            mask=False,
        )
        attach_json(f"axe-{level.upper()} results", {"violations": result.violations}, mask=False)
        log.info(result.summary())
        return result
