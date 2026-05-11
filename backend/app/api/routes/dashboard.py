from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.api.schemas import DashboardStats, PublishQueueRead
from app.database.models import PublishQueue, PublishStatus


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(require_admin)])


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(session: AsyncSession = Depends(get_db)) -> DashboardStats:
    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    published_today = await _count(
        session,
        PublishQueue.status == PublishStatus.published,
        PublishQueue.published_at >= today_start,
    )
    pending = await _count(session, PublishQueue.status.in_([PublishStatus.pending, PublishStatus.scheduled]))
    processing = await _count(session, PublishQueue.status == PublishStatus.processing)
    errors = await _count(session, PublishQueue.status == PublishStatus.failed)
    return DashboardStats(
        published_today=published_today,
        pending=pending,
        processing=processing,
        errors=errors,
    )


@router.get("/recent", response_model=list[PublishQueueRead])
async def recent_posts(session: AsyncSession = Depends(get_db)) -> list[PublishQueue]:
    stmt = (
        select(PublishQueue)
        .where(PublishQueue.status == PublishStatus.published)
        .order_by(PublishQueue.published_at.desc())
        .limit(10)
    )
    return list((await session.scalars(stmt)).all())


async def _count(session: AsyncSession, *conditions) -> int:
    stmt = select(func.count()).select_from(PublishQueue)
    for condition in conditions:
        stmt = stmt.where(condition)
    return int(await session.scalar(stmt) or 0)

