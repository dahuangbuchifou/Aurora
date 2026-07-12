"""CLI for explicit Aurora payload migration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aurora.db.payload_migration import migrate_payloads


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate Aurora JSON payloads")
    parser.add_argument("--database", required=True)
    parser.add_argument("--from", dest="from_version", default="1.0")
    parser.add_argument("--to", dest="to_version", default="1.1")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--object-type")
    parser.add_argument("--workspace-id")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = migrate_payloads(
        database_url=args.database,
        from_version=args.from_version,
        to_version=args.to_version,
        dry_run=args.dry_run,
        backup_dir=args.backup_dir,
        batch_size=args.batch_size,
        object_type=args.object_type,
        workspace_id=args.workspace_id,
        fail_fast=args.fail_fast,
        report_path=args.report,
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if report.failed_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
