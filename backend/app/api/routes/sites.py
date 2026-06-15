from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.api.schemas import (
    WordPressAuthorRead,
    WordPressCategoryRead,
    WordPressSiteCreate,
    WordPressSiteRead,
    WordPressSiteUpdate,
)
from app.database.models import WordPressSite
from app.security import decrypt_secret, encrypt_secret
from app.services.audit import add_audit_log
from app.services.settings_store import read_global_settings


router = APIRouter(prefix="/api/sites", tags=["sites"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[WordPressSiteRead])
async def list_sites(session: AsyncSession = Depends(get_db)) -> list[WordPressSite]:
    return list((await session.scalars(select(WordPressSite).order_by(WordPressSite.name))).all())


@router.post("", response_model=WordPressSiteRead, status_code=status.HTTP_201_CREATED)
async def create_site(payload: WordPressSiteCreate, session: AsyncSession = Depends(get_db)) -> WordPressSite:
    plugin_token = (payload.plugin_token or "").strip()
    site = WordPressSite(
        name=payload.name,
        base_url=payload.base_url.rstrip("/"),
        username=payload.username,
        encrypted_app_password=encrypt_secret(payload.app_password),
        encrypted_plugin_token=encrypt_secret(plugin_token) if plugin_token else None,
        default_status=payload.default_status,
        default_category_ids=payload.default_category_ids,
        default_tag_ids=payload.default_tag_ids,
        is_active=payload.is_active,
    )
    session.add(site)
    try:
        await session.flush()
        add_audit_log(
            session,
            event="site_created",
            message=f"Site WordPress criado: {site.name}",
            payload={"site_id": site.id, "base_url": site.base_url},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Site já cadastrado") from exc
    await session.refresh(site)
    return site


@router.get("/{site_id}", response_model=WordPressSiteRead)
async def get_site(site_id: int, session: AsyncSession = Depends(get_db)) -> WordPressSite:
    return await _site_or_404(session, site_id)


@router.put("/{site_id}", response_model=WordPressSiteRead)
async def update_site(
    site_id: int,
    payload: WordPressSiteUpdate,
    session: AsyncSession = Depends(get_db),
) -> WordPressSite:
    site = await _site_or_404(session, site_id)
    values = payload.model_dump(exclude_unset=True)
    app_password = values.pop("app_password", None)
    if app_password:
        site.encrypted_app_password = encrypt_secret(app_password)
    plugin_token = values.pop("plugin_token", None)
    if plugin_token and plugin_token.strip():
        site.encrypted_plugin_token = encrypt_secret(plugin_token.strip())
    if "base_url" in values and values["base_url"]:
        values["base_url"] = values["base_url"].rstrip("/")
    for key, value in values.items():
        setattr(site, key, value)
    add_audit_log(
        session,
        event="site_updated",
        message=f"Site WordPress atualizado: {site.name}",
        payload={"site_id": site.id, "fields": sorted(values.keys())},
    )
    await session.commit()
    await session.refresh(site)
    return site


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(site_id: int, session: AsyncSession = Depends(get_db)) -> None:
    site = await _site_or_404(session, site_id)
    add_audit_log(
        session,
        event="site_deleted",
        message=f"Site WordPress removido: {site.name}",
        payload={"site_id": site.id, "base_url": site.base_url},
    )
    await session.delete(site)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Site possui registros relacionados") from exc


@router.post("/{site_id}/test")
async def test_site(site_id: int, session: AsyncSession = Depends(get_db)) -> dict[str, object]:
    site = await _site_or_404(session, site_id)
    plugin_token = _site_plugin_token_or_400(site)

    url = site.base_url.rstrip("/") + "/wp-json/email-extractor/v1/status"

    async def _do_test() -> httpx.Response:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            return await client.get(
                url,
                headers={"Authorization": f"Bearer {plugin_token}"},
            )

    try:
        resp = await _do_test()
    except httpx.ConnectError as exc:
        site.last_status = "error"
        site.last_checked_at = datetime.now(timezone.utc)
        await session.commit()
        raise HTTPException(status_code=400, detail=f"Não foi possível conectar ao site: {exc}") from exc
    except Exception as exc:
        site.last_status = "error"
        site.last_checked_at = datetime.now(timezone.utc)
        await session.commit()
        raise HTTPException(status_code=400, detail=f"Erro inesperado: {exc}") from exc

    if resp.status_code == 404:
        site.last_status = "plugin_missing"
        site.last_checked_at = datetime.now(timezone.utc)
        await session.commit()
        raise HTTPException(
            status_code=400,
            detail="Plugin Email Extractor Bridge não encontrado neste site. Instale e ative o plugin.",
        )

    if resp.status_code in (401, 403):
        site.last_status = "auth_failed"
        site.last_checked_at = datetime.now(timezone.utc)
        await session.commit()
        raise HTTPException(
            status_code=400,
            detail="Token do plugin não confere. Verifique o token no cadastro do site e no painel do WordPress.",
        )

    if not resp.is_success:
        site.last_status = "error"
        site.last_checked_at = datetime.now(timezone.utc)
        await session.commit()
        raise HTTPException(status_code=400, detail=f"Resposta inesperada do plugin: HTTP {resp.status_code}")

    site.last_status = "connected"
    site.last_checked_at = datetime.now(timezone.utc)
    await session.commit()
    return {"ok": True, "status": "connected", "message": "Conexão OK — chave API validada pelo plugin"}


@router.get("/{site_id}/categories", response_model=list[WordPressCategoryRead])
async def list_site_categories(site_id: int, session: AsyncSession = Depends(get_db)) -> list[dict[str, object]]:
    site = await _site_or_404(session, site_id)
    plugin_token = _site_plugin_token_or_400(site)
    url = site.base_url.rstrip("/") + "/wp-json/email-extractor/v1/categories"

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {plugin_token}"})
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=400, detail=f"Não foi possível conectar ao site: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erro inesperado ao consultar categorias: {exc}") from exc

    if resp.status_code == 404:
        raise HTTPException(
            status_code=400,
            detail="Plugin Email Extractor Bridge não encontrado ou desatualizado. Atualize o plugin no WordPress.",
        )
    if resp.status_code in (401, 403):
        raise HTTPException(
            status_code=400,
            detail="Token do plugin não confere. Verifique o token no cadastro do site e no painel do WordPress.",
        )
    if not resp.is_success:
        raise HTTPException(status_code=400, detail=f"Resposta inesperada do plugin: HTTP {resp.status_code}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Plugin retornou resposta inválida ao consultar categorias") from exc

    raw_categories = data.get("categories") if isinstance(data, dict) else data
    if not isinstance(raw_categories, list):
        raise HTTPException(status_code=400, detail="Plugin retornou categorias em formato inválido")

    categories: list[dict[str, object]] = []
    for item in raw_categories:
        if not isinstance(item, dict):
            continue
        try:
            category_id = int(item["id"])
        except (KeyError, TypeError, ValueError):
            continue
        try:
            count = int(item.get("count") or 0)
        except (TypeError, ValueError):
            count = 0
        categories.append(
            {
                "id": category_id,
                "name": str(item.get("name") or f"Categoria #{category_id}"),
                "slug": str(item.get("slug") or ""),
                "count": count,
            }
        )
    return categories


@router.get("/{site_id}/authors", response_model=list[WordPressAuthorRead])
async def list_site_authors(site_id: int, session: AsyncSession = Depends(get_db)) -> list[dict[str, object]]:
    site = await _site_or_404(session, site_id)
    plugin_token = _site_plugin_token_or_400(site)
    url = site.base_url.rstrip("/") + "/wp-json/email-extractor/v1/authors"

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {plugin_token}"})
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=400, detail=f"Não foi possível conectar ao site: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erro inesperado ao consultar autores: {exc}") from exc

    if resp.status_code == 404:
        return await _list_site_authors_from_wordpress_rest(site)
    if resp.status_code in (401, 403):
        raise HTTPException(
            status_code=400,
            detail="Token do plugin não confere. Verifique o token no cadastro do site e no painel do WordPress.",
        )
    if not resp.is_success:
        raise HTTPException(status_code=400, detail=f"Resposta inesperada do plugin: HTTP {resp.status_code}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Plugin retornou resposta inválida ao consultar autores") from exc

    raw_authors = data.get("authors") if isinstance(data, dict) else data
    authors = _normalize_author_items(raw_authors)
    if not authors:
        return await _list_site_authors_from_wordpress_rest(site)
    return authors


async def _list_site_authors_from_wordpress_rest(site: WordPressSite) -> list[dict[str, object]]:
    password = decrypt_secret(site.encrypted_app_password)
    url = site.base_url.rstrip("/") + "/wp-json/wp/v2/users"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                url,
                params={"context": "edit", "per_page": 100},
                auth=(site.username, password),
            )
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=400, detail=f"Não foi possível conectar ao site: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erro inesperado ao consultar autores: {exc}") from exc

    if resp.status_code in (401, 403):
        raise HTTPException(
            status_code=400,
            detail="Usuário ou senha de aplicativo do WordPress não permitem listar autores.",
        )
    if not resp.is_success:
        raise HTTPException(status_code=400, detail=f"Resposta inesperada do WordPress: HTTP {resp.status_code}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="WordPress retornou resposta inválida ao consultar autores") from exc
    return _normalize_author_items(data)


def _normalize_author_items(raw_authors: object) -> list[dict[str, object]]:
    if not isinstance(raw_authors, list):
        return []

    authors: list[dict[str, object]] = []
    seen_usernames: set[str] = set()
    for item in raw_authors:
        if not isinstance(item, dict):
            continue
        try:
            author_id = int(item["id"])
        except (KeyError, TypeError, ValueError):
            continue
        username = str(item.get("username") or item.get("slug") or "").strip()
        if not username or username in seen_usernames:
            continue
        seen_usernames.add(username)
        authors.append(
            {
                "id": author_id,
                "name": str(item.get("name") or username),
                "username": username,
            }
        )
    return authors


def _site_plugin_token_or_400(site: WordPressSite) -> str:
    if site.encrypted_plugin_token:
        return decrypt_secret(site.encrypted_plugin_token)

    # Compatibilidade temporária com instalações que usavam uma chave global.
    global_settings = read_global_settings()
    global_token = str(global_settings.get("api_secret_key") or "").strip()
    if global_token:
        return global_token

    raise HTTPException(
        status_code=400,
        detail="Token do plugin não configurado para este site. Edite o site e informe o token em 'Token do Plugin'.",
    )


async def _site_or_404(session: AsyncSession, site_id: int) -> WordPressSite:
    site = await session.get(WordPressSite, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site não encontrado")
    return site
