"""add sqlite_path to documents

Revision ID: b1a1b2c3d4e5
Revises: 8d9e2efd309c
Create Date: 2026-02-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1a1b2c3d4e5"
down_revision: Union[str, None] = "8d9e2efd309c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("sqlite_path", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "sqlite_path")
