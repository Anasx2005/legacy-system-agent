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


class EvidenceSource(Base):
    __tablename__ = "evidence_sources"

    id = Column(Integer, primary_key=True)

    system_id = Column(
        Integer,
        ForeignKey("legacy_systems.id"),
        nullable=False,
    )

    source_type = Column(String(100))

    location = Column(Text)

    description = Column(Text)

    added_at = Column(DateTime)

    system = relationship(
        "LegacySystem",
        back_populates="evidence_sources",
    )