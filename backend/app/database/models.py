import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class PublishStatus(str, enum.Enum):
    pending = "pending"
    scheduled = "scheduled"
    processing = "processing"
    published = "published"
    failed = "failed"
    cancelled = "cancelled"


class LogLevel(str, enum.Enum):
    info = "info"
    warning = "warning"
    error = "error"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EmailAccount(TimestampMixin, Base):
    __tablename__ = "email_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    imap_host: Mapped[str] = mapped_column(String(255), nullable=False, default="imap.gmail.com")
    imap_port: Mapped[int] = mapped_column(Integer, nullable=False, default=993)
    use_ssl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    folder: Mapped[str] = mapped_column(String(120), nullable=False, default="INBOX")
    processed_folder: Mapped[str | None] = mapped_column(String(120))
    polling_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    last_seen_uid: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    match_rules: Mapped[list["MatchRule"]] = relationship(back_populates="email_account")
    queue_items: Mapped[list["PublishQueue"]] = relationship(back_populates="email_account")
    logs: Mapped[list["PublishLog"]] = relationship(back_populates="email_account")


class WordPressSite(TimestampMixin, Base):
    __tablename__ = "wordpress_sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_app_password: Mapped[str] = mapped_column(Text, nullable=False)
    auth_type: Mapped[str] = mapped_column(String(40), nullable=False, default="application_password")
    default_status: Mapped[str] = mapped_column(String(20), nullable=False, default="publish")
    default_category_ids: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    default_tag_ids: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_status: Mapped[str | None] = mapped_column(String(80))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    match_rules: Mapped[list["MatchRule"]] = relationship(back_populates="wordpress_site")
    queue_items: Mapped[list["PublishQueue"]] = relationship(back_populates="wordpress_site")
    logs: Mapped[list["PublishLog"]] = relationship(back_populates="wordpress_site")


class MatchRule(TimestampMixin, Base):
    __tablename__ = "match_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email_account_id: Mapped[int] = mapped_column(ForeignKey("email_accounts.id"), nullable=False)
    wordpress_site_id: Mapped[int] = mapped_column(ForeignKey("wordpress_sites.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sender_contains: Mapped[str | None] = mapped_column(String(255))
    sender_name_contains: Mapped[str | None] = mapped_column(String(255))
    subject_regex: Mapped[str | None] = mapped_column(String(500))
    category_ids: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    tag_ids: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    author_username: Mapped[str | None] = mapped_column(String(120))
    post_status: Mapped[str] = mapped_column(String(20), nullable=False, default="publish")
    delay_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    remove_signature: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    remove_footer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    convert_bold_to_h3: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    extract_gallery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    custom_cut_regex: Mapped[str | None] = mapped_column(String(500))
    custom_cut_selector: Mapped[str | None] = mapped_column(String(500))

    email_account: Mapped[EmailAccount] = relationship(back_populates="match_rules")
    wordpress_site: Mapped[WordPressSite] = relationship(back_populates="match_rules")
    queue_items: Mapped[list["PublishQueue"]] = relationship(back_populates="match_rule")


class PublishQueue(TimestampMixin, Base):
    __tablename__ = "publish_queue"
    __table_args__ = (
        UniqueConstraint("email_account_id", "email_uid", name="uq_publish_queue_account_uid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email_account_id: Mapped[int] = mapped_column(ForeignKey("email_accounts.id"), nullable=False)
    match_rule_id: Mapped[int] = mapped_column(ForeignKey("match_rules.id"), nullable=False)
    wordpress_site_id: Mapped[int] = mapped_column(ForeignKey("wordpress_sites.id"), nullable=False)
    email_uid: Mapped[str] = mapped_column(String(120), nullable=False)
    email_message_id: Mapped[str | None] = mapped_column(String(500))
    email_subject: Mapped[str] = mapped_column(String(500), nullable=False)
    email_from: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    parsed_title: Mapped[str | None] = mapped_column(String(500))
    parsed_excerpt: Mapped[str | None] = mapped_column(Text)
    parsed_content_html: Mapped[str | None] = mapped_column(Text)
    featured_image_url: Mapped[str | None] = mapped_column(Text)
    gallery_image_urls: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[PublishStatus] = mapped_column(
        Enum(PublishStatus, name="publish_status"),
        nullable=False,
        default=PublishStatus.pending,
        index=True,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    post_id: Mapped[int | None] = mapped_column(Integer)
    post_url: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    last_error: Mapped[str | None] = mapped_column(Text)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    email_account: Mapped[EmailAccount] = relationship(back_populates="queue_items")
    match_rule: Mapped[MatchRule] = relationship(back_populates="queue_items")
    wordpress_site: Mapped[WordPressSite] = relationship(back_populates="queue_items")
    logs: Mapped[list["PublishLog"]] = relationship(back_populates="queue_item")


class PublishLog(TimestampMixin, Base):
    __tablename__ = "publish_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    queue_id: Mapped[int | None] = mapped_column(ForeignKey("publish_queue.id"))
    email_account_id: Mapped[int | None] = mapped_column(ForeignKey("email_accounts.id"))
    wordpress_site_id: Mapped[int | None] = mapped_column(ForeignKey("wordpress_sites.id"))
    level: Mapped[LogLevel] = mapped_column(
        Enum(LogLevel, name="publish_log_level"),
        nullable=False,
        default=LogLevel.info,
        index=True,
    )
    event: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    content_preview: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_detail: Mapped[str | None] = mapped_column(Text)

    queue_item: Mapped[PublishQueue | None] = relationship(back_populates="logs")
    email_account: Mapped[EmailAccount | None] = relationship(back_populates="logs")
    wordpress_site: Mapped[WordPressSite | None] = relationship(back_populates="logs")

