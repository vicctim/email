from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.api.schemas import GlobalSettings
from app.services.settings_store import read_global_settings, update_global_settings


router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_admin)])


@router.get("")
async def get_settings() -> dict[str, Any]:
    return read_global_settings()


@router.put("")
async def put_settings(payload: GlobalSettings) -> dict[str, Any]:
    values = payload.model_dump(exclude_unset=True)
    extra = values.pop("extra", None) or {}
    values.update(extra)
    return update_global_settings(values)

