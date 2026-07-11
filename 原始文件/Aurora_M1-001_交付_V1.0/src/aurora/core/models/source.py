"""Source-level objects."""

from datetime import datetime
from typing import Literal

from pydantic import Field, HttpUrl

from .common import BaseObject, new_id
from .enums import ObjectType, SourceQualityTier, SourceType


class Source(BaseObject):
    id: str = Field(default_factory=lambda: new_id("src"))
    object_type: Literal[ObjectType.SOURCE] = ObjectType.SOURCE
    name: str = Field(min_length=1, max_length=500)
    source_type: SourceType
    publisher: str | None = None
    author: str | None = None
    homepage_url: HttpUrl | None = None
    domain: str | None = None
    source_quality_tier: SourceQualityTier = SourceQualityTier.S5
    ownership_or_interest: str | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
