from backend.repository.legacy_system_repository import (
    create_legacy_system,
)

from backend.repository.model_element_index_repository import (
    upsert_model_element,
)



def test_upsert_create_model_element(db_session):
    system = create_legacy_system(
        db=db_session,
        name="ERP",
    )

    element = upsert_model_element(
        db=db_session,
        system_id=system.id,
        git_path="backend/main.py",
        layer="Application",
        archimate_type="ApplicationComponent",
        name="Main Component",
        current_commit="abc123",
    )

    assert element.id is not None
    assert element.system_id == system.id
    assert element.git_path == "backend/main.py"
    assert element.layer == "Application"





def test_upsert_update_model_element(db_session):
    system = create_legacy_system(
        db=db_session,
        name="ERP",
    )

    first = upsert_model_element(
        db=db_session,
        system_id=system.id,
        git_path="backend/main.py",
        layer="Application",
        archimate_type="ApplicationComponent",
        name="Old Name",
        current_commit="abc123",
    )

    updated = upsert_model_element(
        db=db_session,
        system_id=system.id,
        git_path="backend/main.py",
        layer="Technology",
        archimate_type="Node",
        name="New Name",
        current_commit="def456",
    )

    assert updated.id == first.id
    assert updated.layer == "Technology"
    assert updated.archimate_type == "Node"
    assert updated.name == "New Name"
    assert updated.current_commit == "def456"


    