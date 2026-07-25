from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import relationship

from backend.database.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)

    system_id = Column(
        Integer,
        ForeignKey("legacy_systems.id"),
        nullable=False,
    )

    phase = Column(String(100), nullable=False)

    status = Column(String(50), nullable=False)

    run_id = Column(String(255))

    error_message = Column(Text)

    started_at = Column(DateTime)

    finished_at = Column(DateTime)

    system = relationship(
        "LegacySystem",
        back_populates="jobs",
    )