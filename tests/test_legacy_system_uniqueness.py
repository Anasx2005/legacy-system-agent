import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.database.models.legacy_system import LegacySystem


def test_legacy_system_name_must_be_unique():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        session.add(LegacySystem(name="legacy-system"))
        session.commit()

        session.add(LegacySystem(name="legacy-system"))
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.close()
        engine.dispose()
