from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models.legacy_system import LegacySystem

def create_legacy_system(
    db: Session,
    name: str,
    description: str | None = None,
) -> LegacySystem:

    system = LegacySystem(
        name=name,
        description=description,
    )

    db.add(system)

    db.commit()

    db.refresh(system)

    return system


def get_legacy_system(
    db: Session,
    system_id: int,
) -> LegacySystem | None:

    statement = select(LegacySystem).where(
        LegacySystem.id == system_id
    )

    result = db.execute(statement)

    return result.scalar_one_or_none()