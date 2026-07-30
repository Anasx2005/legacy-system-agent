"""make legacy system names unique

Revision ID: c4e7b9d1a2f0
Revises: f34d8a319778
Create Date: 2026-07-30
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c4e7b9d1a2f0"
down_revision: Union[str, Sequence[str], None] = "f34d8a319778"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge duplicate systems before enforcing the natural key.

    The lowest ID is retained.  Child records are moved to it; records that
    would violate an existing child uniqueness rule are discarded because an
    equivalent canonical record already exists.
    """
    # These two tables already enforce uniqueness per system.  Remove a
    # duplicate-side record only when moving it would collide with its
    # canonical equivalent.
    op.execute(
        """
        DELETE FROM model_element_index AS duplicate_element
        USING legacy_systems AS duplicate_system,
              legacy_systems AS canonical_system,
              model_element_index AS canonical_element
        WHERE duplicate_element.system_id = duplicate_system.id
          AND duplicate_system.name = canonical_system.name
          AND canonical_system.id < duplicate_system.id
          AND canonical_element.system_id = canonical_system.id
          AND canonical_element.git_path = duplicate_element.git_path
        """
    )
    op.execute(
        """
        DELETE FROM artifact_versions AS duplicate_artifact
        USING legacy_systems AS duplicate_system,
              legacy_systems AS canonical_system,
              artifact_versions AS canonical_artifact
        WHERE duplicate_artifact.system_id = duplicate_system.id
          AND duplicate_system.name = canonical_system.name
          AND canonical_system.id < duplicate_system.id
          AND duplicate_artifact.run_id IS NOT NULL
          AND canonical_artifact.system_id = canonical_system.id
          AND canonical_artifact.run_id = duplicate_artifact.run_id
        """
    )

    for table_name in (
        "jobs",
        "evidence_sources",
        "model_element_index",
        "artifact_versions",
    ):
        op.execute(
            f"""
            UPDATE {table_name} AS child
            SET system_id = canonical_system.id
            FROM legacy_systems AS duplicate_system
            JOIN legacy_systems AS canonical_system
              ON canonical_system.name = duplicate_system.name
             AND canonical_system.id < duplicate_system.id
            WHERE child.system_id = duplicate_system.id
            """
        )

    op.execute(
        """
        DELETE FROM legacy_systems AS duplicate_system
        USING legacy_systems AS canonical_system
        WHERE duplicate_system.name = canonical_system.name
          AND canonical_system.id < duplicate_system.id
        """
    )
    op.create_unique_constraint(
        "uq_legacy_systems_name", "legacy_systems", ["name"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_legacy_systems_name", "legacy_systems", type_="unique")
