from dotenv import load_dotenv
from sqlalchemy import select

load_dotenv()

from backend.database.models.legacy_system import LegacySystem
from backend.database.session import SessionLocal


SYSTEM_NAME = "legacy-system"

db = SessionLocal()

try:
    system = db.execute(
        select(LegacySystem).where(
            LegacySystem.name == SYSTEM_NAME
        )
    ).scalar_one_or_none()

    if system is None:
        system = LegacySystem(
            name=SYSTEM_NAME,
            description="Model repository system used for Epic G automation.",
        )
        db.add(system)
        db.commit()
        db.refresh(system)
        print(f"created: id={system.id}, name={system.name}")
    else:
        print(f"already exists: id={system.id}, name={system.name}")

finally:
    db.close()