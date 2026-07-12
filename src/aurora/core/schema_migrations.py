"""Pure payload adapters between Aurora schema versions.

Adapters operate on deep copies and never write to the database. They must not
invent business facts when an older payload does not contain a V1.1 field.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from .models.common import LEGACY_SCHEMA_VERSION, SCHEMA_VERSION
from .models.enums import DerivationRelationType, ObjectType


class SchemaVersionError(ValueError):
    """Base error for unsupported or malformed schema-version payloads."""


class MissingSchemaVersionError(SchemaVersionError):
    pass


class UnsupportedSchemaVersionError(SchemaVersionError):
    pass


def _deduplicated_origin_ids(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, str) and value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def upgrade_payload_v1_0_to_v1_1(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a V1.1 copy of a valid-looking V1.0 payload.

    The function intentionally uses conservative defaults:
    - no currency or accounting standard is guessed;
    - claims receive the neutral ``general`` dimension;
    - legacy origins become generic ``derived_from`` links.
    """

    upgraded = deepcopy(payload)
    version = upgraded.get("schema_version")
    if version is None:
        raise MissingSchemaVersionError("payload is missing schema_version")
    if version != LEGACY_SCHEMA_VERSION:
        raise UnsupportedSchemaVersionError(
            f"expected schema_version={LEGACY_SCHEMA_VERSION}, got {version!r}"
        )

    raw_type = upgraded.get("object_type")
    try:
        object_type = ObjectType(raw_type)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"unsupported object_type: {raw_type!r}") from exc

    if object_type == ObjectType.DATA_POINT:
        upgraded.setdefault(
            "measurement_context",
            {
                "measurement_kind": "unknown",
                "currency": None,
                "scale_multiplier": 1,
                "reporting_standard": None,
                "attribution_scope": None,
                "consolidation_scope": None,
            },
        )
    elif object_type == ObjectType.CLAIM:
        upgraded.setdefault("claim_dimension", "general")

    provenance = upgraded.get("provenance")
    if isinstance(provenance, dict):
        derivation_links = provenance.get("derivation_links")
        if derivation_links is None:
            origins = _deduplicated_origin_ids(
                provenance.get("origin_object_ids", [])
            )
            provenance["derivation_links"] = [
                {
                    "object_id": object_id,
                    "relation_type": DerivationRelationType.DERIVED_FROM.value,
                    "note": "legacy V1.0 compatibility mapping",
                }
                for object_id in origins
            ]

    upgraded["schema_version"] = SCHEMA_VERSION
    return upgraded


PayloadAdapter = Callable[[dict[str, Any]], dict[str, Any]]

_ADAPTERS: dict[tuple[str, str], PayloadAdapter] = {
    (LEGACY_SCHEMA_VERSION, SCHEMA_VERSION): upgrade_payload_v1_0_to_v1_1,
}


def upgrade_payload(
    payload: dict[str, Any],
    *,
    target_version: str = SCHEMA_VERSION,
) -> dict[str, Any]:
    """Upgrade a payload to ``target_version`` without mutating the input."""

    source_version = payload.get("schema_version")
    if source_version is None:
        raise MissingSchemaVersionError("payload is missing schema_version")
    if source_version == target_version:
        return deepcopy(payload)

    adapter = _ADAPTERS.get((str(source_version), target_version))
    if adapter is None:
        raise UnsupportedSchemaVersionError(
            f"no schema adapter from {source_version!r} to {target_version!r}"
        )
    return adapter(payload)
