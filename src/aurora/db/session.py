"""Database engine and session helpers."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_SQLITE_TIMEOUT_SECONDS = 30.0
SQLITE_TIMEOUT_ENV = "AURORA_SQLITE_TIMEOUT_SECONDS"


def _ensure_sqlite_parent(database_url: str) -> None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return
    raw_path = database_url[len(prefix):]
    if raw_path in {":memory:", ""} or raw_path.startswith("file:"):
        return
    Path(raw_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def _sqlite_timeout_seconds(explicit: float | None) -> float:
    if explicit is not None:
        timeout = float(explicit)
    else:
        raw = os.getenv(SQLITE_TIMEOUT_ENV)
        timeout = float(raw) if raw is not None else DEFAULT_SQLITE_TIMEOUT_SECONDS
    if timeout < 0:
        raise ValueError("SQLite timeout cannot be negative")
    return timeout


def create_db_engine(
    database_url: str,
    *,
    echo: bool = False,
    sqlite_timeout_seconds: float | None = None,
) -> Engine:
    _ensure_sqlite_parent(database_url)

    is_sqlite = database_url.startswith("sqlite")
    timeout = _sqlite_timeout_seconds(sqlite_timeout_seconds) if is_sqlite else None
    connect_args = (
        {
            "check_same_thread": False,
            "timeout": timeout,
        }
        if is_sqlite
        else {}
    )
    engine = create_engine(
        database_url,
        echo=echo,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )

    if is_sqlite:
        busy_timeout_ms = int((timeout or 0) * 1000)

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
