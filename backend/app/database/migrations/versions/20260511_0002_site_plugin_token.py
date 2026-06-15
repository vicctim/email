"""add per-site plugin token

Revision ID: 20260511_0002
Revises: 20260511_0001
Create Date: 2026-05-11 00:02:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260511_0002"
down_revision: Union[str, None] = "20260511_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("wordpress_sites", sa.Column("encrypted_plugin_token", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("wordpress_sites", "encrypted_plugin_token")
