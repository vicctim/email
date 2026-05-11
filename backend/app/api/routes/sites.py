from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.api.schemas import WordPressSiteCreate, WordPressSiteRead, WordPressSiteUpdate
from app.database.models import WordPressSite
from app.security import decrypt_secret, encrypt_secret
from app.services.audit import add_audit_log


router = APIRouter(prefix="/api/sites", tags=["sites"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[WordPressSiteRead])
async def list_sites(session: AsyncSession = Depends(get_db)) -> list[WordPressSite]:
    return list((await session.scalars(select(WordPressSite).order_by(WordPressSite.name))).all())


@router.post("", response_model=WordPressSiteRead, status_code=status.HTTP_201_CREATED)
async def create_site(payload: WordPressSiteCreate, session: AsyncSession = Depends(get_db)) -> WordPressSite:
    site = WordPressSite(
        name=payload.name,
        base_url=payload.base_url.rstrip("/"),
        username=payload.username,
        encrypted_app_password=encrypt_secret(payload.app_password),
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
    url = site.base_url.rstrip("/") + "/wp-json/wp/v2/users/me"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, auth=(site.username, decrypt_secret(site.encrypted_app_password)))
            response.raise_for_status()
    except Exception as exc:
        site.last_status = "error"
        site.last_checked_at = datetime.now(timezone.utc)
        await session.commit()
        raise HTTPException(status_code=400, detail=f"Falha ao conectar no WordPress: {exc}") from exc

    site.last_status = "connected"
    site.last_checked_at = datetime.now(timezone.utc)
    await session.commit()
    return {"ok": True, "status": "connected"}


async def _site_or_404(session: AsyncSession, site_id: int) -> WordPressSite:
    site = await session.get(WordPressSite, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site não encontrado")
    return site
