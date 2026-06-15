import asyncio

from pytest import MonkeyPatch

from app.database.models import MatchRule, PublishQueue, WordPressSite
from app.security import encrypt_secret
from app.services import wp_publisher
from app.services.wp_publisher import WordPressPublisher


def test_publish_prefers_plugin_endpoint_when_token_is_configured(monkeypatch: MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "status": "ok",
                "post_id": 123,
                "post_url": "https://example.test/post",
            }

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            captured["client_kwargs"] = kwargs

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> FakeResponse:
            captured["url"] = url
            captured["request_kwargs"] = kwargs
            return FakeResponse()

    monkeypatch.setattr(wp_publisher.httpx, "AsyncClient", FakeClient)

    site = WordPressSite(
        id=1,
        name="Site Teste",
        base_url="https://example.test",
        username="admin",
        encrypted_app_password=encrypt_secret("app-password"),
        encrypted_plugin_token=encrypt_secret("plugin-token"),
    )
    rule = MatchRule(
        id=1,
        email_account_id=1,
        wordpress_site_id=1,
        name="Regra",
        category_ids=[4],
        tag_ids=[9],
        post_status="publish",
    )
    queue_item = PublishQueue(
        id=1,
        email_account_id=1,
        match_rule_id=1,
        wordpress_site_id=1,
        email_uid="42",
        email_subject="Assunto",
        email_from="sender@example.test",
        parsed_title="Titulo",
        parsed_content_html="<blockquote>Olho</blockquote><p>Texto</p>",
        parsed_excerpt="Resumo",
        featured_image_url="https://cdn.example.test/featured.jpg",
        gallery_image_urls=["https://cdn.example.test/gallery.jpg"],
        wordpress_site=site,
        match_rule=rule,
    )

    result = asyncio.run(WordPressPublisher()._publish(queue_item))

    assert result == {"post_id": 123, "post_url": "https://example.test/post", "status": "ok"}
    assert captured["url"] == "https://example.test/wp-json/email-extractor/v1/publish"
    assert captured["client_kwargs"] == {"timeout": 30.0, "follow_redirects": True}

    request_kwargs = captured["request_kwargs"]
    assert isinstance(request_kwargs, dict)
    assert request_kwargs["headers"] == {"Authorization": "Bearer plugin-token"}
    assert request_kwargs["json"] == {
        "title": "Titulo",
        "content": "<blockquote>Olho</blockquote>\n<p>Texto</p>",
        "excerpt": "Resumo",
        "status": "publish",
        "categories": [4],
        "tags": [9],
        "featured_image_url": "https://cdn.example.test/featured.jpg",
        "gallery_images": ["https://cdn.example.test/gallery.jpg"],
    }


def test_publish_sets_selected_author_when_configured(monkeypatch: MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []

    class FakeResponse:
        def __init__(self, payload: object) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> object:
            return self.payload

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            return None

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str, **kwargs: object) -> FakeResponse:
            calls.append(("GET", url, kwargs))
            return FakeResponse([{"id": 77, "name": "Editor", "username": "editor", "slug": "editor"}])

        async def post(self, url: str, **kwargs: object) -> FakeResponse:
            calls.append(("POST", url, kwargs))
            if url.endswith("/wp-json/email-extractor/v1/publish"):
                return FakeResponse({"status": "ok", "post_id": 123, "post_url": "https://example.test/post"})
            return FakeResponse({"id": 123, "author": 77})

    monkeypatch.setattr(wp_publisher.httpx, "AsyncClient", FakeClient)

    site = WordPressSite(
        id=1,
        name="Site Teste",
        base_url="https://example.test",
        username="admin",
        encrypted_app_password=encrypt_secret("app-password"),
        encrypted_plugin_token=encrypt_secret("plugin-token"),
    )
    rule = MatchRule(
        id=1,
        email_account_id=1,
        wordpress_site_id=1,
        name="Regra",
        author_username="editor",
        post_status="publish",
    )
    queue_item = PublishQueue(
        id=1,
        email_account_id=1,
        match_rule_id=1,
        wordpress_site_id=1,
        email_uid="42",
        email_subject="Assunto",
        email_from="sender@example.test",
        parsed_title="Titulo",
        parsed_content_html="<p>Texto</p>",
        gallery_image_urls=[],
        wordpress_site=site,
        match_rule=rule,
    )

    result = asyncio.run(WordPressPublisher()._publish(queue_item))

    assert result["post_id"] == 123
    assert [call[0] for call in calls] == ["GET", "POST", "POST"]
    assert calls[0][1] == "https://example.test/wp-json/wp/v2/users"
    assert calls[1][1] == "https://example.test/wp-json/email-extractor/v1/publish"
    assert calls[1][2]["json"]["author_username"] == "editor"
    assert calls[1][2]["json"]["author_id"] == 77
    assert calls[2][1] == "https://example.test/wp-json/wp/v2/posts/123"
    assert calls[2][2]["json"] == {"author": 77}
