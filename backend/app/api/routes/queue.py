from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.api.schemas import PublishQueueRead, QueuePreview
from app.database.models import PublishQueue, PublishStatus
from app.workers.tasks import publish_to_wordpress


router = APIRouter(prefix="/api/queue", tags=["queue"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[PublishQueueRead])
async def list_queue(
    status_filter: PublishStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> list[PublishQueue]:
    stmt = select(PublishQueue).order_by(PublishQueue.created_at.desc()).limit(limit).offset(offset)
    if status_filter:
        stmt = stmt.where(PublishQueue.status == status_filter)
    return list((await session.scalars(stmt)).all())


@router.post("/{queue_id}/cancel", response_model=PublishQueueRead)
async def cancel_queue_item(queue_id: int, session: AsyncSession = Depends(get_db)) -> PublishQueue:
    queue_item = await _queue_or_404(session, queue_id)
    if queue_item.status not in {PublishStatus.published, PublishStatus.processing}:
        queue_item.status = PublishStatus.cancelled
        queue_item.last_error = None
        await session.commit()
        await session.refresh(queue_item)
    return queue_item


@router.post("/{queue_id}/retry", response_model=PublishQueueRead)
async def retry_queue_item(queue_id: int, session: AsyncSession = Depends(get_db)) -> PublishQueue:
    queue_item = await _queue_or_404(session, queue_id)
    if queue_item.status == PublishStatus.processing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Item já está em processamento")
    queue_item.status = PublishStatus.scheduled
    queue_item.attempts = 0
    queue_item.last_error = None
    queue_item.scheduled_at = datetime.now(timezone.utc)
    queue_item.started_at = None
    queue_item.published_at = None
    queue_item.post_id = None
    queue_item.post_url = None
    await session.commit()
    await session.refresh(queue_item)
    publish_to_wordpress.apply_async(args=[queue_item.id], queue="publish")
    return queue_item


@router.get("/{queue_id}/preview", response_model=QueuePreview)
async def preview_queue_item(queue_id: int, session: AsyncSession = Depends(get_db)) -> QueuePreview:
    queue_item = await _queue_or_404(session, queue_id)
    return QueuePreview(
        title=queue_item.parsed_title,
        excerpt=queue_item.parsed_excerpt,
        content_html=queue_item.parsed_content_html,
        featured_image_url=queue_item.featured_image_url,
        gallery_image_urls=queue_item.gallery_image_urls,
    )


async def _queue_or_404(session: AsyncSession, queue_id: int) -> PublishQueue:
    queue_item = await session.get(PublishQueue, queue_id)
    if queue_item is None:
        raise HTTPException(status_code=404, detail="Item de fila não encontrado")
    return queue_item
