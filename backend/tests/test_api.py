import asyncio
import time
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from pytest import MonkeyPatch


def test_admin_crud_sites_accounts_rules(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: MonkeyPatch,
) -> None:
    suffix = int(time.time() * 1000)

    site_response = client.post(
        "/api/sites",
        json={
            "name": f"Smoke WP {suffix}",
            "base_url": f"https://wp-smoke-{suffix}.test",
            "username": "admin",
            "app_password": "secret",
            "plugin_token": "plugin-secret",
            "default_status": "draft",
        },
        headers=auth_headers,
    )
    assert site_response.status_code == 201, site_response.text
    site_id = site_response.json()["id"]

    account_response = client.post(
        "/api/accounts",
        json={
            "name": f"Smoke Gmail {suffix}",
            "username": f"smoke-{suffix}@gmail.com",
            "password": "secret",
        },
        headers=auth_headers,
    )
    assert account_response.status_code == 201, account_response.text
    account_id = account_response.json()["id"]

    rule_response = client.post(
        "/api/rules",
        json={
            "name": f"Smoke Rule {suffix}",
            "email_account_id": account_id,
            "wordpress_site_id": site_id,
            "sender_contains": "example.com",
            "subject_regex": "Release",
        },
        headers=auth_headers,
    )
    assert rule_response.status_code == 201, rule_response.text
    rule_id = rule_response.json()["id"]

    assert client.get("/api/sites", headers=auth_headers).status_code == 200
    assert client.get("/api/accounts", headers=auth_headers).status_code == 200
    assert client.get("/api/rules", headers=auth_headers).status_code == 200

    from app.services.imap_listener import AccountConfig, ImapListener

    run_call: dict[str, int] = {}

    def fake_run_single_rule(self: ImapListener, config: AccountConfig) -> int:
        run_call["account_id"] = config.id
        run_call["rule_id"] = config.rules[0].id
        return 2

    monkeypatch.setattr(ImapListener, "run_single_rule_config", fake_run_single_rule)

    run_response = client.post(f"/api/rules/{rule_id}/run", headers=auth_headers)
    assert run_response.status_code == 200, run_response.text
    assert run_response.json()["processed"] == 2
    assert run_call == {"account_id": account_id, "rule_id": rule_id}

    def fake_imap_failure(self: ImapListener, config: AccountConfig) -> int:
        raise RuntimeError("IMAP indisponível")

    monkeypatch.setattr(ImapListener, "run_single_rule_config", fake_imap_failure)

    run_failure_response = client.post(f"/api/rules/{rule_id}/run", headers=auth_headers)
    assert run_failure_response.status_code == 502, run_failure_response.text
    assert run_failure_response.json()["detail"] == "Falha ao verificar caixa de email: IMAP indisponível"

    toggle_response = client.patch(f"/api/rules/{rule_id}/toggle", headers=auth_headers)
    assert toggle_response.status_code == 200
    assert toggle_response.json()["active"] is False

    from app.database.connection import session_factory
    from app.database.models import PublishQueue, PublishStatus

    async def create_published_queue_item() -> int:
        async with session_factory() as session:
            queue_item = PublishQueue(
                email_account_id=account_id,
                match_rule_id=rule_id,
                wordpress_site_id=site_id,
                email_uid=f"published-{suffix}",
                email_subject="Assunto fallback",
                email_from="sender@example.com",
                parsed_title=f"Titulo publicado {suffix}",
                gallery_image_urls=[],
                status=PublishStatus.published,
                published_at=datetime.now(timezone.utc),
                post_url=f"https://wp-smoke-{suffix}.test/post-publicado",
            )
            session.add(queue_item)
            await session.commit()
            return queue_item.id

    queue_id = asyncio.run(create_published_queue_item())

    recent_response = client.get("/api/dashboard/recent", headers=auth_headers)
    assert recent_response.status_code == 200, recent_response.text
    recent_items = recent_response.json()
    recent_item = next(item for item in recent_items if item["id"] == queue_id)
    assert recent_item["title"] == f"Titulo publicado {suffix}"
    assert recent_item["site_name"] == f"Smoke WP {suffix}"
    assert recent_item["site_url"] == f"https://wp-smoke-{suffix}.test"

    stats_response = client.get("/api/dashboard/stats", headers=auth_headers)
    assert stats_response.status_code == 200
    stats_body = stats_response.json()
    assert {
        "published_today",
        "pending",
        "processing",
        "errors",
        "failed",
        "total_published",
        "active_sites",
        "active_rules",
    } <= set(stats_body)
    assert stats_body["published_today"] >= 1
    assert stats_body["failed"] == stats_body["errors"]
    assert stats_body["total_published"] >= 1
    assert stats_body["active_sites"] >= 1
    assert stats_body["active_rules"] >= 0

    from app.api.routes import queue as queue_routes

    queued_publish: dict[str, object] = {}

    def fake_publish_apply_async(*, args: list[int], queue: str) -> None:
        queued_publish["args"] = args
        queued_publish["queue"] = queue

    monkeypatch.setattr(queue_routes.publish_to_wordpress, "apply_async", fake_publish_apply_async)

    retry_response = client.post(f"/api/queue/{queue_id}/retry", headers=auth_headers)
    assert retry_response.status_code == 200, retry_response.text
    retry_body = retry_response.json()
    assert retry_body["status"] == "scheduled"
    assert retry_body["published_at"] is None
    assert retry_body["post_url"] is None
    assert queued_publish == {"args": [queue_id], "queue": "publish"}

    logs_response = client.get("/api/logs", headers=auth_headers)
    assert logs_response.status_code == 200
    events = {item["event"] for item in logs_response.json()}
    assert {"admin_login", "site_created", "account_created", "rule_created"} <= events

    async def delete_queue_item() -> None:
        async with session_factory() as session:
            queue_item = await session.get(PublishQueue, queue_id)
            if queue_item:
                await session.delete(queue_item)
                await session.commit()

    asyncio.run(delete_queue_item())

    assert client.delete(f"/api/rules/{rule_id}", headers=auth_headers).status_code == 204
    assert client.delete(f"/api/accounts/{account_id}", headers=auth_headers).status_code == 204
    assert client.delete(f"/api/sites/{site_id}", headers=auth_headers).status_code == 204
