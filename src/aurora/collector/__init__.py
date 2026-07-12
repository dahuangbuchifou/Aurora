"""Offline and static collectors."""

from .base import CollectedInput, Collector
from .local_file import LocalBinaryFileCollector, LocalFileCollector

try:  # Optional parser extra.
    from .static_url import StaticUrlCollector
except Exception:  # pragma: no cover - import stays optional for core installs.
    StaticUrlCollector = None  # type: ignore[assignment]

__all__ = [
    "CollectedInput",
    "Collector",
    "LocalFileCollector",
    "LocalBinaryFileCollector",
    "StaticUrlCollector",
]
