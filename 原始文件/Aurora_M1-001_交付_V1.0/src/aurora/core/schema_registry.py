"""Object registry, payload parsing, and JSON Schema export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from .models import (
    AuroraObject,
    Claim,
    ContentUnit,
    DataPoint,
    Document,
    Entity,
    Event,
    Evidence,
    Fact,
    Feedback,
    Insight,
    KnowledgeObject,
    OutputArtifact,
    PersonalOpinion,
    ProcessingRun,
    Relation,
    Source,
    TimelineEntry,
)
from .models.common import BaseObject
from .models.enums import ObjectType

MODEL_REGISTRY: dict[ObjectType, type[BaseObject]] = {
    ObjectType.SOURCE: Source,
    ObjectType.DOCUMENT: Document,
    ObjectType.CONTENT_UNIT: ContentUnit,
    ObjectType.ENTITY: Entity,
    ObjectType.EVENT: Event,
    ObjectType.DATA_POINT: DataPoint,
    ObjectType.CLAIM: Claim,
    ObjectType.EVIDENCE: Evidence,
    ObjectType.FACT: Fact,
    ObjectType.KNOWLEDGE_OBJECT: KnowledgeObject,
    ObjectType.RELATION: Relation,
    ObjectType.TIMELINE_ENTRY: TimelineEntry,
    ObjectType.INSIGHT: Insight,
    ObjectType.PERSONAL_OPINION: PersonalOpinion,
    ObjectType.OUTPUT_ARTIFACT: OutputArtifact,
    ObjectType.FEEDBACK: Feedback,
    ObjectType.PROCESSING_RUN: ProcessingRun,
}

AURORA_OBJECT_ADAPTER = TypeAdapter(AuroraObject)


def parse_object(payload: dict[str, Any]) -> BaseObject:
    raw_type = payload.get("object_type")
    if raw_type is None:
        raise ValueError("payload is missing object_type")
    try:
        object_type = ObjectType(raw_type)
    except ValueError as exc:
        raise ValueError(f"unsupported object_type: {raw_type}") from exc
    return MODEL_REGISTRY[object_type].model_validate(payload)


def export_json_schemas(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for object_type, model_class in MODEL_REGISTRY.items():
        schema = model_class.model_json_schema()
        schema["$id"] = f"https://aurora.local/schemas/v1/{object_type.value}.schema.json"
        target = output_dir / f"{object_type.value}.schema.json"
        target.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(target)
    registry_path = output_dir / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "objects": {
                    object_type.value: f"{object_type.value}.schema.json"
                    for object_type in MODEL_REGISTRY
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    written.append(registry_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Aurora JSON Schemas")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("schemas/v1"),
        help="Schema output directory",
    )
    args = parser.parse_args()
    written = export_json_schemas(args.output)
    print(f"Exported {len(written) - 1} object schemas to {args.output}")


if __name__ == "__main__":
    main()
