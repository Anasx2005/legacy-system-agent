import pytest
from sqlalchemy.orm import Session

from backend.database.session import SessionLocal


@pytest.fixture
def db_session() -> Session:
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()