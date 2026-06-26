"""add manual approval fields

Revision ID: 20260511_0003
Revises: 20260511_0002
Create Date: 2026-06-24 16:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260511_0003"
down_revision: Union[str, None] = "20260511_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "wordpress_sites",
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "publish_queue",
        sa.Column("needs_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "publish_queue",
        sa.Column("approval_token", sa.String(128), nullable=True),
    )
    op.add_column(
        "publish_queue",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("publish_queue", "approved_at")
    op.drop_column("publish_queue", "approval_token")
    op.drop_column("publish_queue", "needs_approval")
    op.drop_column("wordpress_sites", "approval_required")