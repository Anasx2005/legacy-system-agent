import pytest

from backend.repository.legacy_system_repository import (
    create_legacy_system,
    get_legacy_system,
)


def test_create_legacy_system(db_session):

    system = create_legacy_system(
        db=db_session,
        name="ERP System",
        description="Test Legacy System",
    )

    assert system.id is not None
    assert system.name == "ERP System"
    assert system.description == "Test Legacy System"


def test_get_legacy_system(db_session):

    created = create_legacy_system(
        db=db_session,
        name="ERP",
        description="Legacy",
    )

    found = get_legacy_system(
        db=db_session,
        system_id=created.id,
    )

    assert found is not None
    assert found.id == created.id
    assert found.name == "ERP"    