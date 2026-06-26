"""add approval_required to match_rules

Revision ID: 20260624_0004
Revises: 20260511_0003
Create Date: 2026-06-25 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_0004"
down_revision: Union[str, None] = "20260511_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "match_rules",
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("match_rules", "approval_required")