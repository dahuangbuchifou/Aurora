"""Export JSON Schemas for application-level ingestion contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import IngestionRequest, IngestionResult, StructuredSegmentsManifest

INGESTION_CONTRACT_VERSION = "1.1"
CONTRACTS = {
    "ingestion_request": IngestionRequest,
    "ingestion_result": IngestionResult,
    "structured_segments": StructuredSegmentsManifest,
}


def export_ingestion_schemas(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    schema_path = "v1_1" if INGESTION_CONTRACT_VERSION == "1.1" else "v1"
    for name, model in CONTRACTS.items():
        schema = model.model_json_schema()
        schema["$id"] = (
            "https://aurora.local/schemas/ingestion/"
            f"{schema_path}/{name}.schema.json"
        )
        target = output_dir / f"{name}.schema.json"
        target.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(target)
    registry = output_dir / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "schema_version": INGESTION_CONTRACT_VERSION,
                "contracts": {name: f"{name}.schema.json" for name in CONTRACTS},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    written.append(registry)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Aurora ingestion contract schemas"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("schemas/ingestion/v1_1"),
    )
    args = parser.parse_args()
    written = export_ingestion_schemas(args.output)
    print(f"Exported {len(written) - 1} ingestion schemas to {args.output}")


if __name__ == "__main__":  # pragma: no cover
    main()
