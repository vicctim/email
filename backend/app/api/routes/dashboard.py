import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_admin
from app.api.schemas import DashboardRecentPost, DashboardStats
from app.database.models import MatchRule, PublishQueue, PublishStatus, WordPressSite
from app.services.timezone import local_day_bounds_utc


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(require_admin)])

WEEKDAYS_ABBR = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(session: AsyncSession = Depends(get_db)) -> DashboardStats:
    today_start, tomorrow_start = local_day_bounds_utc()
    published_today = await _count(
        session,
        PublishQueue.status == PublishStatus.published,
        PublishQueue.published_at >= today_start,
        PublishQueue.published_at < tomorrow_start,
    )
    pending = await _count(session, PublishQueue.status.in_([PublishStatus.pending, PublishStatus.scheduled]))
    processing = await _count(session, PublishQueue.status == PublishStatus.processing)
    errors = await _count(session, PublishQueue.status == PublishStatus.failed)
    total_published = await _count(session, PublishQueue.status == PublishStatus.published)
    active_sites = await _count_model(session, WordPressSite, WordPressSite.is_active.is_(True))
    active_rules = await _count_model(session, MatchRule, MatchRule.active.is_(True))
    weekly_chart = await _build_weekly_chart(session)
    return DashboardStats(
        published_today=published_today,
        pending=pending,
        processing=processing,
        errors=errors,
        failed=errors,
        total_published=total_published,
        active_sites=active_sites,
        active_rules=active_rules,
        weekly_chart=weekly_chart,
    )


async def _build_weekly_chart(session: AsyncSession) -> list[dict[str, Any]]:
    """Agrupa publicações dos últimos 7 dias por dia local."""
    from app.services.timezone import local_tz

    today = datetime.now(timezone.utc)
    cutoff = today - timedelta(days=6)

    # Busca todos os published_at bruto sem GROUP BY, depois agrupa em Python
    rows = list(
        (
            await session.scalars(
                select(PublishQueue.published_at)
                .where(
                    PublishQueue.status == PublishStatus.published,
                    PublishQueue.published_at >= cutoff,
                )
            )
        ).all()
    )

    counts_by_day: dict[str, int] = {}
    for published_at in rows:
        if published_at is None:
            continue
        local_dt = published_at.astimezone(local_tz())
        key = local_dt.strftime("%Y-%m-%d")
        counts_by_day[key] = counts_by_day.get(key, 0) + 1

    chart: list[dict[str, Any]] = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        d_local = d.astimezone(local_tz())
        key = d_local.strftime("%Y-%m-%d")
        chart.append({
            "day": WEEKDAYS_ABBR[d_local.weekday()],
            "posts": counts_by_day.get(key, 0),
        })
    return chart


@router.get("/recent", response_model=list[DashboardRecentPost])
async def recent_posts(session: AsyncSession = Depends(get_db)) -> list[DashboardRecentPost]:
    stmt = (
        select(PublishQueue)
        .where(PublishQueue.status == PublishStatus.published)
        .options(selectinload(PublishQueue.wordpress_site))
        .order_by(PublishQueue.published_at.desc())
        .limit(10)
    )
    queue_items = list((await session.scalars(stmt)).all())
    return [
        DashboardRecentPost(
            id=item.id,
            title=item.parsed_title or item.email_subject or "Sem título",
            site_name=item.wordpress_site.name if item.wordpress_site else f"Site #{item.wordpress_site_id}",
            site_url=item.wordpress_site.base_url if item.wordpress_site else "",
            post_url=item.post_url,
            published_at=item.published_at or item.updated_at or item.created_at,
            status=item.status,
        )
        for item in queue_items
    ]


async def _count(session: AsyncSession, *conditions) -> int:
    return await _count_model(session, PublishQueue, *conditions)


async def _count_model(session: AsyncSession, model, *conditions) -> int:
    stmt = select(func.count()).select_from(model)
    for condition in conditions:
        stmt = stmt.where(condition)
    return int(await session.scalar(stmt) or 0)
