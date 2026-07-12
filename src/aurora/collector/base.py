"""Collector interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CollectedInput:
    path: Path | None
    input_uri: str
    file_name: str
    suffix: str
    size_bytes: int
    text: str
    raw_bytes: bytes = b""
    media_type: str | None = None
    response_metadata: dict[str, Any] = field(default_factory=dict)


class Collector(ABC):
    @abstractmethod
    def collect(self, *args, **kwargs) -> CollectedInput:
        raise NotImplementedError
