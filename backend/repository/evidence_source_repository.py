from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models.evidence_source import EvidenceSource

def create_evidence_source(
    db: Session,
    system_id: int,
    source_type: str,
    location: str | None = None,
    description: str | None = None,
) -> EvidenceSource:

    source = EvidenceSource(
        system_id=system_id,
        source_type=source_type,
        location=location,
        description=description,
    )

    db.add(source)
    db.commit()
    db.refresh(source)

    return source





def list_evidence_sources(
    db: Session,
    system_id: int,
) -> list[EvidenceSource]:

    statement = (
        select(EvidenceSource)
        .where(EvidenceSource.system_id == system_id)
    )

    result = db.execute(statement)

    return list(result.scalars().all())



    
