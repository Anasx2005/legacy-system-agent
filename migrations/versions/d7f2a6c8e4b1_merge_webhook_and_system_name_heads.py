"""merge webhook and system name migration heads

Revision ID: d7f2a6c8e4b1
Revises: 10acc11c3b8e, c4e7b9d1a2f0
Create Date: 2026-07-30
"""

from typing import Sequence, Union


revision: str = "d7f2a6c8e4b1"
down_revision: Union[str, Sequence[str], None] = (
    "10acc11c3b8e",
    "c4e7b9d1a2f0",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
