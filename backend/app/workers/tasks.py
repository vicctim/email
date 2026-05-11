import asyncio
import base64
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser

from celery.utils.log import get_task_logger
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.database.connection import session_factory
from app.database.models import LogLevel, MatchRule, PublishLog, PublishQueue, PublishStatus
from app.services.email_parser import EmailParser
from app.services.imap_listener import run_polling_cycle
from app.services.whatsapp_notifier import WhatsAppNotifier
from app.services.wp_publisher import WordPressPublisher
from app.workers.celery_app import celery_app


logger = get_task_logger(__name__)


def _run(coro):
    return asyncio.run(coro)


@celery_app.task(name="app.workers.tasks.process_email")
def process_email(
    *,
    email_account_id: int,
    match_rule_id: int,
    email_uid: str,
    raw_email_b64: str,
) -> dict[str, object]:
    return _run(
        _process_email(
            email_account_id=email_account_id,
            match_rule_id=match_rule_id,
            email_uid=email_uid,
            raw_email_b64=raw_email_b64,
        )
    )


async def _process_email(
    *,
    email_account_id: int,
    match_rule_id: int,
    email_uid: str,
    raw_email_b64: str,
) -> dict[str, object]:
    raw_email = base64.b64decode(raw_email_b64)
    message = BytesParser(policy=policy.default).parsebytes(raw_email)

    async with session_factory() as session:
        rule = await session.scalar(
            select(MatchRule)
            .where(MatchRule.id == match_rule_id)
            .options(selectinload(MatchRule.wordpress_site), selectinload(MatchRule.email_account))
        )
        if rule is None:
            raise ValueError(f"Regra não encontrada: {match_rule_id}")

        existing = await session.scalar(
            select(PublishQueue).where(
                PublishQueue.email_account_id == email_account_id,
                PublishQueue.email_uid == email_uid,
            )
        )
        if existing:
            return {"queue_id": existing.id, "status": existing.status.value}

        parsed = EmailParser().parse_message(
            raw_email,
            remove_signature=rule.remove_signature,
            remove_footer=rule.remove_footer,
            convert_bold_to_h3=rule.convert_bold_to_h3,
            extract_gallery=rule.extract_gallery,
        )

        scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=rule.delay_minutes)
        queue_item = PublishQueue(
            email_account_id=email_account_id,
            match_rule_id=rule.id,
            wordpress_site_id=rule.wordpress_site_id,
            email_uid=email_uid,
            email_message_id=str(message.get("message-id", "") or "") or None,
            email_subject=str(message.get("subject", "") or ""),
            email_from=str(message.get("from", "") or ""),
            content_hash=parsed.content_hash,
            parsed_title=parsed.title,
            parsed_excerpt=parsed.excerpt,
            parsed_content_html=parsed.content_html,
            featured_image_url=parsed.featured_image_url,
            gallery_image_urls=parsed.gallery_image_urls,
            status=PublishStatus.scheduled,
            scheduled_at=scheduled_at,
            max_attempts=3,
        )
        session.add(queue_item)
        await session.flush()
        session.add(
            PublishLog(
                queue_id=queue_item.id,
                email_account_id=email_account_id,
                wordpress_site_id=rule.wordpress_site_id,
                level=LogLevel.info,
                event="email_processed",
                message=f"E-mail processado e agendado para {scheduled_at.isoformat()}",
                content_preview=parsed.content_html[:1000],
                payload=parsed.as_dict(),
            )
        )

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            existing = await session.scalar(
                select(PublishQueue).where(
                    PublishQueue.email_account_id == email_account_id,
                    PublishQueue.email_uid == email_uid,
                )
            )
            if existing:
                return {"queue_id": existing.id, "status": existing.status.value}
            raise

        publish_to_wordpress.apply_async(
            args=[queue_item.id],
            countdown=max(rule.delay_minutes, 0) * 60,
            queue="publish",
        )
        return {"queue_id": queue_item.id, "status": queue_item.status.value}


@celery_app.task(name="app.workers.tasks.publish_to_wordpress")
def publish_to_wordpress(queue_id: int) -> dict[str, object]:
    return _run(_publish_to_wordpress(queue_id))


async def _publish_to_wordpress(queue_id: int) -> dict[str, object]:
    async with session_factory() as session:
        queue_item = await session.scalar(
            select(PublishQueue)
            .where(PublishQueue.id == queue_id)
            .options(selectinload(PublishQueue.wordpress_site))
        )
        if queue_item is None:
            raise ValueError(f"Item de fila não encontrado: {queue_id}")
        if queue_item.status == PublishStatus.cancelled:
            return {"queue_id": queue_id, "status": "cancelled"}

        title = queue_item.parsed_title or queue_item.email_subject
        site_name = queue_item.wordpress_site.name if queue_item.wordpress_site else ""

    try:
        async with session_factory() as session:
            result = await WordPressPublisher().publish_queue_item(session, queue_id)
            queue_item = await session.get(PublishQueue, queue_id)
            if queue_item:
                session.add(
                    PublishLog(
                        queue_id=queue_id,
                        email_account_id=queue_item.email_account_id,
                        wordpress_site_id=queue_item.wordpress_site_id,
                        level=LogLevel.info,
                        event="post_published",
                        message=f"Publicação concluída com status {result.get('status')}",
                        payload=result,
                    )
                )
                await session.commit()

        if result.get("status") != "duplicate":
            send_whatsapp_notification.apply_async(
                kwargs={
                    "kind": "success",
                    "title": title,
                    "site": site_name,
                    "url": result.get("post_url"),
                },
                queue="notify",
            )
        return {"queue_id": queue_id, **result}
    except Exception as exc:
        logger.exception("Falha ao publicar item %s", queue_id)
        async with session_factory() as session:
            queue_item = await session.get(PublishQueue, queue_id)
            if queue_item:
                queue_item.status = PublishStatus.failed
                queue_item.last_error = str(exc)
                session.add(
                    PublishLog(
                        queue_id=queue_id,
                        email_account_id=queue_item.email_account_id,
                        wordpress_site_id=queue_item.wordpress_site_id,
                        level=LogLevel.error,
                        event="publish_failed",
                        message="Falha ao publicar no WordPress",
                        error_detail=str(exc),
                    )
                )
                await session.commit()
        send_whatsapp_notification.apply_async(
            kwargs={"kind": "error", "title": title, "error": str(exc)},
            queue="notify",
        )
        raise


@celery_app.task(name="app.workers.tasks.send_whatsapp_notification")
def send_whatsapp_notification(
    *,
    kind: str,
    title: str,
    site: str | None = None,
    url: str | None = None,
    error: str | None = None,
) -> bool:
    return _run(
        _send_whatsapp_notification(kind=kind, title=title, site=site, url=url, error=error)
    )


async def _send_whatsapp_notification(
    *,
    kind: str,
    title: str,
    site: str | None,
    url: str | None,
    error: str | None,
) -> bool:
    notifier = WhatsAppNotifier()
    if kind == "success":
        return await notifier.send_success(title=title, site=site or "", url=url)
    return await notifier.send_error(title=title, error=error or "Erro desconhecido")


@celery_app.task(name="app.workers.tasks.check_imap_inbox")
def check_imap_inbox() -> int:
    return _run(run_polling_cycle())


@celery_app.task(name="app.workers.tasks.cleanup_old_logs")
def cleanup_old_logs(days: int = 90) -> int:
    return _run(_cleanup_old_logs(days))


async def _cleanup_old_logs(days: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with session_factory() as session:
        result = await session.execute(delete(PublishLog).where(PublishLog.created_at < cutoff))
        await session.commit()
        return int(result.rowcount or 0)

