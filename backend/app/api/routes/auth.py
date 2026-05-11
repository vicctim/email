from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas import AuthLogin, TokenResponse
from app.config import get_settings
from app.security import create_access_token, verify_password
from app.services.audit import add_audit_log


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: AuthLogin, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    settings = get_settings()
    if payload.username != settings.admin_username or not verify_password(
        payload.password,
        settings.admin_password,
    ):
        add_audit_log(
            session,
            event="admin_login_failed",
            message=f"Tentativa de login falhou para {payload.username}",
            payload={"username": payload.username},
        )
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    add_audit_log(
        session,
        event="admin_login",
        message=f"Login administrativo realizado por {payload.username}",
        payload={"username": payload.username},
    )
    await session.commit()
    return TokenResponse(access_token=create_access_token(payload.username))
