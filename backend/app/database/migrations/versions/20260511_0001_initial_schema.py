"""initial schema

Revision ID: 20260511_0001
Revises:
Create Date: 2026-05-11 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260511_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


publish_status = postgresql.ENUM(
    "pending",
    "scheduled",
    "processing",
    "published",
    "failed",
    "cancelled",
    name="publish_status",
    create_type=False,
)
publish_log_level = postgresql.ENUM(
    "info",
    "warning",
    "error",
    name="publish_log_level",
    create_type=False,
)


def upgrade() -> None:
    publish_status.create(op.get_bind(), checkfirst=True)
    publish_log_level.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "email_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("imap_host", sa.String(length=255), nullable=False),
        sa.Column("imap_port", sa.Integer(), nullable=False),
        sa.Column("use_ssl", sa.Boolean(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("encrypted_password", sa.Text(), nullable=False),
        sa.Column("folder", sa.String(length=120), nullable=False),
        sa.Column("processed_folder", sa.String(length=120), nullable=True),
        sa.Column("polling_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("last_seen_uid", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "wordpress_sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("encrypted_app_password", sa.Text(), nullable=False),
        sa.Column("auth_type", sa.String(length=40), nullable=False),
        sa.Column("default_status", sa.String(length=20), nullable=False),
        sa.Column("default_category_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("default_tag_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_status", sa.String(length=80), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("base_url"),
    )

    op.create_table(
        "match_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email_account_id", sa.Integer(), nullable=False),
        sa.Column("wordpress_site_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("sender_contains", sa.String(length=255), nullable=True),
        sa.Column("sender_name_contains", sa.String(length=255), nullable=True),
        sa.Column("subject_regex", sa.String(length=500), nullable=True),
        sa.Column("category_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tag_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("author_username", sa.String(length=120), nullable=True),
        sa.Column("post_status", sa.String(length=20), nullable=False),
        sa.Column("delay_minutes", sa.Integer(), nullable=False),
        sa.Column("remove_signature", sa.Boolean(), nullable=False),
        sa.Column("remove_footer", sa.Boolean(), nullable=False),
        sa.Column("convert_bold_to_h3", sa.Boolean(), nullable=False),
        sa.Column("extract_gallery", sa.Boolean(), nullable=False),
        sa.Column("custom_cut_regex", sa.String(length=500), nullable=True),
        sa.Column("custom_cut_selector", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["email_account_id"], ["email_accounts.id"]),
        sa.ForeignKeyConstraint(["wordpress_site_id"], ["wordpress_sites.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "publish_queue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email_account_id", sa.Integer(), nullable=False),
        sa.Column("match_rule_id", sa.Integer(), nullable=False),
        sa.Column("wordpress_site_id", sa.Integer(), nullable=False),
        sa.Column("email_uid", sa.String(length=120), nullable=False),
        sa.Column("email_message_id", sa.String(length=500), nullable=True),
        sa.Column("email_subject", sa.String(length=500), nullable=False),
        sa.Column("email_from", sa.String(length=500), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("parsed_title", sa.String(length=500), nullable=True),
        sa.Column("parsed_excerpt", sa.Text(), nullable=True),
        sa.Column("parsed_content_html", sa.Text(), nullable=True),
        sa.Column("featured_image_url", sa.Text(), nullable=True),
        sa.Column("gallery_image_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", publish_status, nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("post_id", sa.Integer(), nullable=True),
        sa.Column("post_url", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["email_account_id"], ["email_accounts.id"]),
        sa.ForeignKeyConstraint(["match_rule_id"], ["match_rules.id"]),
        sa.ForeignKeyConstraint(["wordpress_site_id"], ["wordpress_sites.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_account_id", "email_uid", name="uq_publish_queue_account_uid"),
    )
    op.create_index(op.f("ix_publish_queue_content_hash"), "publish_queue", ["content_hash"], unique=False)
    op.create_index(op.f("ix_publish_queue_scheduled_at"), "publish_queue", ["scheduled_at"], unique=False)
    op.create_index(op.f("ix_publish_queue_status"), "publish_queue", ["status"], unique=False)

    op.create_table(
        "publish_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("queue_id", sa.Integer(), nullable=True),
        sa.Column("email_account_id", sa.Integer(), nullable=True),
        sa.Column("wordpress_site_id", sa.Integer(), nullable=True),
        sa.Column("level", publish_log_level, nullable=False),
        sa.Column("event", sa.String(length=120), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("content_preview", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["email_account_id"], ["email_accounts.id"]),
        sa.ForeignKeyConstraint(["queue_id"], ["publish_queue.id"]),
        sa.ForeignKeyConstraint(["wordpress_site_id"], ["wordpress_sites.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_publish_logs_level"), "publish_logs", ["level"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_publish_logs_level"), table_name="publish_logs")
    op.drop_table("publish_logs")
    op.drop_index(op.f("ix_publish_queue_status"), table_name="publish_queue")
    op.drop_index(op.f("ix_publish_queue_scheduled_at"), table_name="publish_queue")
    op.drop_index(op.f("ix_publish_queue_content_hash"), table_name="publish_queue")
    op.drop_table("publish_queue")
    op.drop_table("match_rules")
    op.drop_table("wordpress_sites")
    op.drop_table("email_accounts")
    publish_log_level.drop(op.get_bind(), checkfirst=True)
    publish_status.drop(op.get_bind(), checkfirst=True)
