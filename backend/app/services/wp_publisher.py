import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database.models import PublishQueue, PublishStatus
from app.security import decrypt_secret
from app.services.image_handler import ImageHandler


class WordPressPublisher:
    def __init__(self, image_handler: ImageHandler | None = None, timeout: float = 30.0) -> None:
        self.image_handler = image_handler or ImageHandler(timeout=timeout)
        self.timeout = timeout

    async def publish_queue_item(self, session: AsyncSession, queue_id: int) -> dict[str, Any]:
        queue_item = await self._load_queue_item(session, queue_id)
        if queue_item is None:
            raise ValueError(f"Item de fila não encontrado: {queue_id}")

        duplicate = await self._find_duplicate(session, queue_item)
        if duplicate:
            queue_item.status = PublishStatus.cancelled
            queue_item.post_id = duplicate.post_id
            queue_item.post_url = duplicate.post_url
            queue_item.last_error = "Publicação duplicada por content_hash"
            await session.commit()
            return {"post_id": duplicate.post_id, "post_url": duplicate.post_url, "status": "duplicate"}

        max_attempts = queue_item.max_attempts or 3
        last_error: Exception | None = None
        for attempt in range(queue_item.attempts, max_attempts):
            queue_item.attempts = attempt + 1
            queue_item.status = PublishStatus.processing
            queue_item.started_at = datetime.now(timezone.utc)
            await session.commit()

            try:
                result = await self._publish(queue_item)
            except Exception as exc:
                last_error = exc
                queue_item.last_error = str(exc)
                await session.commit()
                if attempt + 1 >= max_attempts:
                    break
                await asyncio.sleep(2**attempt)
                continue

            queue_item.status = PublishStatus.published
            queue_item.published_at = datetime.now(timezone.utc)
            queue_item.post_id = result["post_id"]
            queue_item.post_url = result.get("post_url")
            queue_item.last_error = None
            await session.commit()
            return result

        queue_item.status = PublishStatus.failed
        queue_item.last_error = str(last_error) if last_error else "Falha desconhecida ao publicar"
        await session.commit()
        raise RuntimeError(queue_item.last_error)

    async def _publish(self, queue_item: PublishQueue) -> dict[str, Any]:
        site = queue_item.wordpress_site
        rule = queue_item.match_rule
        if site is None or rule is None:
            raise ValueError("Item da fila precisa carregar site e regra")
        if not queue_item.parsed_title or not queue_item.parsed_content_html:
            raise ValueError("Item da fila não possui conteúdo parseado")

        self._validate_wordpress_url(site.base_url)
        password = decrypt_secret(site.encrypted_app_password)
        featured_media_id = None
        if queue_item.featured_image_url:
            featured_media_id = await self.image_handler.upload_to_wordpress(
                site_url=site.base_url,
                username=site.username,
                app_password=password,
                image_url=queue_item.featured_image_url,
            )

        gallery_ids: list[int] = []
        for image_url in queue_item.gallery_image_urls or []:
            media_id = await self.image_handler.upload_to_wordpress(
                site_url=site.base_url,
                username=site.username,
                app_password=password,
                image_url=image_url,
            )
            gallery_ids.append(media_id)

        content = queue_item.parsed_content_html
        if gallery_ids:
            ids = ",".join(str(media_id) for media_id in gallery_ids)
            content = f'{content}\n\n[email_gallery ids="{ids}"]'

        payload: dict[str, Any] = {
            "title": queue_item.parsed_title,
            "content": content,
            "excerpt": queue_item.parsed_excerpt or "",
            "status": rule.post_status or site.default_status or "publish",
            "categories": rule.category_ids or site.default_category_ids or [],
            "tags": rule.tag_ids or site.default_tag_ids or [],
        }
        if featured_media_id:
            payload["featured_media"] = featured_media_id

        posts_url = site.base_url.rstrip("/") + "/wp-json/wp/v2/posts"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(posts_url, json=payload, auth=(site.username, password))
            response.raise_for_status()

        data = response.json()
        post_id = data.get("id")
        if not isinstance(post_id, int):
            raise ValueError("WordPress não retornou post_id válido")
        return {"post_id": post_id, "post_url": data.get("link"), "status": data.get("status", payload["status"])}

    @staticmethod
    def _validate_wordpress_url(site_url: str) -> None:
        if get_settings().app_env == "production" and site_url.startswith("http://"):
            raise ValueError("WordPress precisa usar HTTPS em produção")

    @staticmethod
    async def _load_queue_item(session: AsyncSession, queue_id: int) -> PublishQueue | None:
        stmt = (
            select(PublishQueue)
            .where(PublishQueue.id == queue_id)
            .options(
                selectinload(PublishQueue.wordpress_site),
                selectinload(PublishQueue.match_rule),
            )
        )
        return await session.scalar(stmt)

    @staticmethod
    async def _find_duplicate(session: AsyncSession, queue_item: PublishQueue) -> PublishQueue | None:
        if not queue_item.content_hash:
            return None
        stmt = (
            select(PublishQueue)
            .where(
                PublishQueue.id != queue_item.id,
                PublishQueue.wordpress_site_id == queue_item.wordpress_site_id,
                PublishQueue.content_hash == queue_item.content_hash,
                PublishQueue.status == PublishStatus.published,
            )
            .limit(1)
        )
        return await session.scalar(stmt)
