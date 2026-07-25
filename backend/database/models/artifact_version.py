from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)

from sqlalchemy.orm import relationship

from backend.database.base import Base


class ArtifactVersion(Base):
    __tablename__ = "artifact_versions"

    id = Column(Integer, primary_key=True)

    system_id = Column(
        Integer,
        ForeignKey("legacy_systems.id"),
        nullable=False,
    )

    commit_sha = Column(String(255))

    phase = Column(String(100))

    tag = Column(String(100))

    author_type = Column(String(50))

    run_id = Column(String(255))

    approval_status = Column(String(50))

    approved_by = Column(String(255))

    approved_at = Column(DateTime)

    created_at = Column(DateTime)

    system = relationship(
        "LegacySystem",
        back_populates="artifact_versions",
    )