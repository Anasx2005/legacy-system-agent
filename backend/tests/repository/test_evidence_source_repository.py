from backend.repository.evidence_source_repository import (
    create_evidence_source,
    list_evidence_sources,
)

from backend.repository.legacy_system_repository import (
    create_legacy_system,
)




def test_create_evidence_source(db_session):
    system = create_legacy_system(
        db=db_session,
        name="ERP",
    )

    source = create_evidence_source(
        db=db_session,
        system_id=system.id,
        source_type="code",
        location="/src",
        description="Source Code",
    )

    assert source.id is not None
    assert source.system_id == system.id
    assert source.source_type == "code"
    assert source.location == "/src"
    assert source.description == "Source Code"



def test_list_evidence_sources(db_session):
    system = create_legacy_system(
        db=db_session,
        name="ERP",
    )

    create_evidence_source(
        db=db_session,
        system_id=system.id,
        source_type="code",
    )

    create_evidence_source(
        db=db_session,
        system_id=system.id,
        source_type="database",
    )

    sources = list_evidence_sources(
        db=db_session,
        system_id=system.id,
    )

    assert len(sources) == 2
