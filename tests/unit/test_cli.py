from types import SimpleNamespace

import pytest


def test_migrate_cli_success(monkeypatch, capsys, tmp_path):
    from aurora.cli import migrate_payloads as module

    report = SimpleNamespace(failed_count=0, to_dict=lambda: {"failed_count": 0})
    monkeypatch.setattr(module, "migrate_payloads", lambda **kwargs: report)
    monkeypatch.setattr(
        "sys.argv",
        [
            "aurora-migrate-payloads",
            "--database",
            "sqlite:///test.db",
            "--dry-run",
            "--report",
            str(tmp_path / "report.json"),
        ],
    )
    module.main()
    assert '"failed_count": 0' in capsys.readouterr().out


def test_migrate_cli_failure_exits(monkeypatch):
    from aurora.cli import migrate_payloads as module

    report = SimpleNamespace(failed_count=1, to_dict=lambda: {"failed_count": 1})
    monkeypatch.setattr(module, "migrate_payloads", lambda **kwargs: report)
    monkeypatch.setattr(
        "sys.argv",
        ["aurora-migrate-payloads", "--database", "sqlite:///test.db", "--dry-run"],
    )
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 1


def test_restore_cli_success(monkeypatch, capsys, tmp_path):
    from aurora.cli import restore_payloads as module

    monkeypatch.setattr(
        module,
        "restore_payloads",
        lambda **kwargs: {"restored_count": 2, "failed_count": 0},
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "aurora-restore-payloads",
            "--database",
            "sqlite:///test.db",
            "--manifest",
            str(tmp_path / "manifest.json"),
        ],
    )
    module.main()
    assert '"restored_count": 2' in capsys.readouterr().out


def test_restore_cli_failure_exits(monkeypatch, tmp_path):
    from aurora.cli import restore_payloads as module

    monkeypatch.setattr(
        module,
        "restore_payloads",
        lambda **kwargs: {"restored_count": 0, "failed_count": 1},
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "aurora-restore-payloads",
            "--database",
            "sqlite:///test.db",
            "--manifest",
            str(tmp_path / "manifest.json"),
            "--backup-current-dir",
            str(tmp_path / "backup"),
            "--report",
            str(tmp_path / "report.json"),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 1
