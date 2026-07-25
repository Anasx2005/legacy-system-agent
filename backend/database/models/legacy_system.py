from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database.base import Base


class LegacySystem(Base):
    __tablename__ = "legacy_systems"

    id = Column(Integer, primary_key=True)

    name = Column(String(255), nullable=False)

    description = Column(Text)

    jobs = relationship("Job", back_populates="system")

    artifact_versions = relationship(
        "ArtifactVersion",
        back_populates="system",
    )

    evidence_sources = relationship(
        "EvidenceSource",
        back_populates="system",
    )

    model_elements = relationship(
        "ModelElementIndex",
        back_populates="system",
    )