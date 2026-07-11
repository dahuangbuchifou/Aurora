from pathlib import Path

import pytest

from aurora.db.base import Base
from aurora.db.session import create_db_engine, create_session_factory


@pytest.fixture()
def db_session(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
