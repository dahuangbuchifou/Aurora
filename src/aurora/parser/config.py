"""Deterministic parser configuration contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aurora.ingestion.hashing import parser_config_hash


@dataclass(frozen=True)
class ParserConfig:
    name: str
    version: str
    options: dict[str, Any]

    @property
    def hash(self) -> str:
        return parser_config_hash(
            {"parser_name": self.name, "parser_version": self.version, **self.options}
        )
