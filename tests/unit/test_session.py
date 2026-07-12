import sqlite3

import pytest
from sqlalchemy import text

from aurora.db.session import (
    SQLITE_TIMEOUT_ENV,
    create_db_engine,
    create_session_factory,
    session_scope,
)


def test_sqlite_timeout_env_sets_busy_timeout(monkeypatch):
    monkeypatch.setenv(SQLITE_TIMEOUT_ENV, "12.5")
    engine = create_db_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        value = connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one()
    engine.dispose()
    assert value == 12_500


def test_explicit_timeout_overrides_env(monkeypatch):
    monkeypatch.setenv(SQLITE_TIMEOUT_ENV, "99")
    engine = create_db_engine(
        "sqlite:///:memory:",
        sqlite_timeout_seconds=2,
    )
    with engine.connect() as connection:
        value = connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one()
    engine.dispose()
    assert value == 2_000


def test_negative_timeout_is_rejected():
    with pytest.raises(ValueError, match="cannot be negative"):
        create_db_engine("sqlite:///:memory:", sqlite_timeout_seconds=-1)


def test_session_scope_commits_and_rolls_back():
    engine = create_db_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE items (id INTEGER PRIMARY KEY)")
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        session.execute(text("INSERT INTO items (id) VALUES (1)"))

    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM items").scalar_one() == 1

    with pytest.raises(RuntimeError):
        with session_scope(factory) as session:
            session.execute(text("INSERT INTO items (id) VALUES (2)"))
            raise RuntimeError("force rollback")

    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM items").scalar_one() == 1
    engine.dispose()
