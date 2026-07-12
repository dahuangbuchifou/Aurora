"""Collector interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CollectedInput:
    path: Path
    input_uri: str
    file_name: str
    suffix: str
    size_bytes: int
    text: str


class Collector(ABC):
    @abstractmethod
    def collect(self, path: Path, *, max_bytes: int) -> CollectedInput:
        raise NotImplementedError
