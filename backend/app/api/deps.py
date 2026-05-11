from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.connection import get_session
from app.security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


async def require_admin(token: str = Depends(oauth2_scheme)) -> str:
    subject = decode_access_token(token)
    if subject != get_settings().admin_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject

