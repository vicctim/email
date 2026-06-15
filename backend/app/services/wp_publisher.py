import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database.models import PublishQueue, PublishStatus, WordPressSite
from app.security import decrypt_secret
from app.services.email_parser import EmailParser
from app.services.image_handler import ImageHandler
from app.services.settings_store import read_global_settings


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

        queue_item.parsed_content_html = self._content_for_publish(queue_item)
        self._validate_wordpress_url(site.base_url)
        plugin_token = self._plugin_token(site)
        if plugin_token:
            return await self._publish_with_plugin(queue_item, plugin_token)

        return await self._publish_with_wordpress_rest(queue_item)

    async def _publish_with_plugin(self, queue_item: PublishQueue, plugin_token: str) -> dict[str, Any]:
        site = queue_item.wordpress_site
        rule = queue_item.match_rule
        if site is None or rule is None:
            raise ValueError("Item da fila precisa carregar site e regra")
        if not queue_item.parsed_title or not queue_item.parsed_content_html:
            raise ValueError("Item da fila não possui conteúdo parseado")

        author_username = (rule.author_username or "").strip()
        author_id = await self._resolve_author_id(site, author_username) if author_username else None
        payload = {
            "title": queue_item.parsed_title,
            "content": queue_item.parsed_content_html,
            "excerpt": queue_item.parsed_excerpt or "",
            "status": rule.post_status or site.default_status or "publish",
            "categories": rule.category_ids or site.default_category_ids or [],
            "tags": rule.tag_ids or site.default_tag_ids or [],
            "featured_image_url": queue_item.featured_image_url or "",
            "gallery_images": queue_item.gallery_image_urls or [],
        }
        if author_username:
            payload["author_username"] = author_username
        if author_id:
            payload["author_id"] = author_id

        publish_url = site.base_url.rstrip("/") + "/wp-json/email-extractor/v1/publish"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.post(
                publish_url,
                json=payload,
                headers={"Authorization": f"Bearer {plugin_token}"},
            )
            response.raise_for_status()

        data = response.json()
        post_id = data.get("post_id")
        if not isinstance(post_id, int):
            raise ValueError("Plugin WordPress não retornou post_id válido")
        if author_id:
            await self._update_post_author(site, post_id, author_id)
        return {"post_id": post_id, "post_url": data.get("post_url"), "status": data.get("status", "ok")}

    async def _publish_with_wordpress_rest(self, queue_item: PublishQueue) -> dict[str, Any]:
        site = queue_item.wordpress_site
        rule = queue_item.match_rule
        if site is None or rule is None:
            raise ValueError("Item da fila precisa carregar site e regra")
        if not queue_item.parsed_title or not queue_item.parsed_content_html:
            raise ValueError("Item da fila não possui conteúdo parseado")

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

        author_username = (rule.author_username or "").strip()
        author_id = await self._resolve_author_id(site, author_username) if author_username else None
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
        if author_id:
            payload["author"] = author_id

        posts_url = site.base_url.rstrip("/") + "/wp-json/wp/v2/posts"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(posts_url, json=payload, auth=(site.username, password))
            response.raise_for_status()

        data = response.json()
        post_id = data.get("id")
        if not isinstance(post_id, int):
            raise ValueError("WordPress não retornou post_id válido")
        return {"post_id": post_id, "post_url": data.get("link"), "status": data.get("status", payload["status"])}

    async def _resolve_author_id(self, site: WordPressSite, author_username: str) -> int:
        password = decrypt_secret(site.encrypted_app_password)
        users_url = site.base_url.rstrip("/") + "/wp-json/wp/v2/users"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(
                users_url,
                params={"context": "edit", "per_page": 100, "search": author_username},
                auth=(site.username, password),
            )
            response.raise_for_status()

        users = response.json()
        if not isinstance(users, list):
            raise ValueError("WordPress retornou lista de autores inválida")

        normalized_username = author_username.casefold()
        for user in users:
            if not isinstance(user, dict):
                continue
            username = str(user.get("username") or "").casefold()
            slug = str(user.get("slug") or "").casefold()
            if username != normalized_username and slug != normalized_username:
                continue
            author_id = user.get("id")
            if isinstance(author_id, int):
                return author_id

        raise ValueError(f"Autor WordPress não encontrado: {author_username}")

    async def _update_post_author(self, site: WordPressSite, post_id: int, author_id: int) -> None:
        password = decrypt_secret(site.encrypted_app_password)
        post_url = site.base_url.rstrip("/") + f"/wp-json/wp/v2/posts/{post_id}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.post(
                post_url,
                json={"author": author_id},
                auth=(site.username, password),
            )
            response.raise_for_status()

    @staticmethod
    def _content_for_publish(queue_item: PublishQueue) -> str:
        return EmailParser().normalize_content_html(
            queue_item.parsed_content_html or "",
            title=queue_item.parsed_title,
        )

    @staticmethod
    def _plugin_token(site: WordPressSite) -> str | None:
        if site.encrypted_plugin_token:
            return decrypt_secret(site.encrypted_plugin_token)

        global_settings = read_global_settings()
        global_token = str(global_settings.get("api_secret_key") or "").strip()
        return global_token or None

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
