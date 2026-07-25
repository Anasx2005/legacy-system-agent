from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from sqlalchemy.orm import relationship

from backend.database.base import Base


class ModelElementIndex(Base):
    __tablename__ = "model_element_index"

    __table_args__ = (
    UniqueConstraint(
        "system_id",
        "git_path",
        name="uq_system_git_path",
    ),
)

    id = Column(Integer, primary_key=True)

    system_id = Column(
        Integer,
        ForeignKey("legacy_systems.id"),
        nullable=False,
    )

    layer = Column(String(100))

    archimate_type = Column(String(100))

    name = Column(String(255))

    git_path = Column(String(500))

    current_commit = Column(String(255))

    updated_at = Column(DateTime)

    system = relationship(
        "LegacySystem",
        back_populates="model_elements",
    )