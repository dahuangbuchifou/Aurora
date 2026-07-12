"""Offline collectors."""

from .base import CollectedInput, Collector
from .local_file import LocalFileCollector

__all__ = ["CollectedInput", "Collector", "LocalFileCollector"]
