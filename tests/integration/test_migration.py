from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _config(project_root, db_path, monkeypatch):
    monkeypatch.delenv("AURORA_DATABASE_URL", raising=False)
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def test_alembic_upgrade_and_downgrade(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[2]
    db_path = tmp_path / "migration.db"
    config = _config(project_root, db_path, monkeypatch)

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    assert "object_records" in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("object_records")}
    assert {"id", "object_type", "payload", "version"} <= columns
    indexes = {item["name"] for item in inspector.get_indexes("object_records")}
    assert "ix_object_records_schema_version" in indexes
    engine.dispose()

    command.downgrade(config, "20260711_0001")
    engine = create_engine(f"sqlite:///{db_path}")
    indexes = {item["name"] for item in inspect(engine).get_indexes("object_records")}
    assert "ix_object_records_schema_version" not in indexes
    engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(f"sqlite:///{db_path}")
    assert "object_records" not in inspect(engine).get_table_names()
    engine.dispose()
