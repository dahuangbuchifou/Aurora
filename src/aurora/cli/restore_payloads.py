"""CLI for restoring Aurora payload backups."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aurora.db.payload_migration import restore_payloads


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore Aurora JSON payloads")
    parser.add_argument("--database", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--backup-current-dir", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    result = restore_payloads(
        database_url=args.database,
        manifest_path=args.manifest,
        backup_current_dir=args.backup_current_dir,
        report_path=args.report,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["failed_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
