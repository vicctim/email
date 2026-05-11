import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _fernet() -> Fernet:
    secret = get_settings().app_secret_key.encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt_secret(value: str | None) -> str:
    if not value:
        return ""
    if value.startswith("fernet:"):
        return value
    return "fernet:" + _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str | None) -> str:
    if not value:
        return ""
    if not value.startswith("fernet:"):
        return value
    try:
        return _fernet().decrypt(value.removeprefix("fernet:").encode()).decode()
    except InvalidToken:
        return ""


def verify_password(plain_password: str, configured_password: str) -> bool:
    if configured_password.startswith("$2") or configured_password.startswith("$argon2"):
        return pwd_context.verify(plain_password, configured_password)
    return hmac.compare_digest(plain_password, configured_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expires}
    return jwt.encode(payload, settings.app_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None

