"""Date/time helpers used for artifact naming, unique data and durations."""

from __future__ import annotations

from datetime import UTC, datetime


def now_iso() -> str:
    """Local time in ISO-8601 format (seconds precision)."""
    return datetime.now().isoformat(timespec="seconds")


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def timestamp(fmt: str = "%Y%m%d_%H%M%S") -> str:
    """Compact timestamp suitable for filenames and generated data."""
    return datetime.now().strftime(fmt)


def timestamp_ms() -> int:
    return int(datetime.now().timestamp() * 1000)


def format_duration(seconds: float) -> str:
    """Convert seconds to ``1h 02m 03s`` / ``45.2s`` style strings."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes}m {secs:02d}s"
