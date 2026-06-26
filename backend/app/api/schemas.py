from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.database.models import LogLevel, PublishStatus


class AuthLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WordPressSiteBase(BaseModel):
    name: str
    base_url: str
    username: str
    default_status: Literal["publish", "draft", "pending"] = "publish"
    default_category_ids: list[int] = Field(default_factory=list)
    default_tag_ids: list[int] = Field(default_factory=list)
    is_active: bool = True


class WordPressSiteCreate(WordPressSiteBase):
    app_password: str
    plugin_token: str | None = None


class WordPressSiteUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    username: str | None = None
    app_password: str | None = None
    plugin_token: str | None = None
    default_status: Literal["publish", "draft", "pending"] | None = None
    default_category_ids: list[int] | None = None
    default_tag_ids: list[int] | None = None
    is_active: bool | None = None


class WordPressSiteRead(WordPressSiteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    auth_type: str
    has_plugin_token: bool = False
    last_status: str | None = None
    last_checked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WordPressCategoryRead(BaseModel):
    id: int
    name: str
    slug: str
    count: int = 0


class WordPressAuthorRead(BaseModel):
    id: int
    name: str
    username: str


class EmailAccountBase(BaseModel):
    name: str
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    use_ssl: bool = True
    username: str
    folder: str = "INBOX"
    processed_folder: str | None = None
    polling_interval_seconds: int = 60
    is_active: bool = True


class EmailAccountCreate(EmailAccountBase):
    password: str


class EmailAccountUpdate(BaseModel):
    name: str | None = None
    imap_host: str | None = None
    imap_port: int | None = None
    use_ssl: bool | None = None
    username: str | None = None
    password: str | None = None
    folder: str | None = None
    processed_folder: str | None = None
    polling_interval_seconds: int | None = None
    is_active: bool | None = None


class EmailAccountRead(EmailAccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_seen_uid: str | None = None
    created_at: datetime
    updated_at: datetime


class MatchRuleBase(BaseModel):
    email_account_id: int
    wordpress_site_id: int
    name: str
    active: bool = True
    sender_contains: str | None = None
    sender_name_contains: str | None = None
    subject_regex: str | None = None
    category_ids: list[int] = Field(default_factory=list)
    tag_ids: list[int] = Field(default_factory=list)
    author_username: str | None = None
    post_status: Literal["publish", "draft", "pending"] = "publish"
    delay_minutes: int = 10
    remove_signature: bool = True
    remove_footer: bool = True
    convert_bold_to_h3: bool = True
    extract_gallery: bool = True
    custom_cut_regex: str | None = None
    custom_cut_selector: str | None = None
    approval_required: bool = False


class MatchRuleCreate(MatchRuleBase):
    pass


class MatchRuleUpdate(BaseModel):
    email_account_id: int | None = None
    wordpress_site_id: int | None = None
    name: str | None = None
    active: bool | None = None
    sender_contains: str | None = None
    sender_name_contains: str | None = None
    subject_regex: str | None = None
    category_ids: list[int] | None = None
    tag_ids: list[int] | None = None
    author_username: str | None = None
    post_status: Literal["publish", "draft", "pending"] | None = None
    delay_minutes: int | None = None
    remove_signature: bool | None = None
    remove_footer: bool | None = None
    convert_bold_to_h3: bool | None = None
    extract_gallery: bool | None = None
    custom_cut_regex: str | None = None
    custom_cut_selector: str | None = None
    approval_required: bool | None = None


class MatchRuleRead(MatchRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PublishQueueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email_account_id: int
    match_rule_id: int
    wordpress_site_id: int
    email_uid: str
    email_message_id: str | None = None
    email_subject: str
    email_from: str
    content_hash: str | None = None
    parsed_title: str | None = None
    parsed_excerpt: str | None = None
    featured_image_url: str | None = None
    gallery_image_urls: list[str]
    status: PublishStatus
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    published_at: datetime | None = None
    post_id: int | None = None
    post_url: str | None = None
    attempts: int
    max_attempts: int
    last_error: str | None = None
    needs_approval: bool = False
    approval_token: str | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class QueuePreview(BaseModel):
    title: str | None
    excerpt: str | None
    content_html: str | None
    featured_image_url: str | None
    gallery_image_urls: list[str]


class DashboardRecentPost(BaseModel):
    id: int
    title: str
    site_name: str
    site_url: str
    post_url: str | None = None
    published_at: datetime
    status: PublishStatus


class PublishLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    queue_id: int | None = None
    email_account_id: int | None = None
    wordpress_site_id: int | None = None
    level: LogLevel
    event: str
    message: str
    content_preview: str | None = None
    payload: dict[str, Any]
    error_detail: str | None = None
    created_at: datetime
    updated_at: datetime


class ApprovalRequest(BaseModel):
    """Recebido do plugin WordPress quando o post é aprovado manualmente."""
    post_id: int
    site_id: int
    approval_token: str


class DashboardStats(BaseModel):
    published_today: int
    pending: int
    processing: int
    errors: int
    failed: int
    total_published: int
    active_sites: int
    active_rules: int
    weekly_chart: list[dict[str, object]] = Field(default_factory=list)


class GlobalSettings(BaseModel):
    default_publish_delay: int | None = None
    polling_interval_seconds: int | None = None
    notifications_enabled: bool | None = None
    whatsapp_notify_number: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
