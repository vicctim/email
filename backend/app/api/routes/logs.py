from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.api.schemas import PublishLogRead
from app.database.models import LogLevel, PublishLog, PublishQueue, PublishStatus


router = APIRouter(prefix="/api/logs", tags=["logs"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[PublishLogRead])
async def list_logs(
    level: LogLevel | None = None,
    site_id: int | None = Query(default=None),
    status: PublishStatus | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> list[PublishLog]:
    stmt = select(PublishLog).order_by(PublishLog.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.join(PublishQueue, PublishQueue.id == PublishLog.queue_id).where(PublishQueue.status == status)
    if level:
        stmt = stmt.where(PublishLog.level == level)
    if site_id:
        stmt = stmt.where(PublishLog.wordpress_site_id == site_id)
    if date_from:
        stmt = stmt.where(PublishLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(PublishLog.created_at <= date_to)
    return list((await session.scalars(stmt)).all())


@router.get("/{log_id}", response_model=PublishLogRead)
async def get_log(log_id: int, session: AsyncSession = Depends(get_db)) -> PublishLog:
    log = await session.get(PublishLog, log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Log não encontrado")
    return log

