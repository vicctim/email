from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import LogLevel, PublishLog


def add_audit_log(
    session: AsyncSession,
    *,
    event: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    session.add(
        PublishLog(
            level=LogLevel.info,
            event=event,
            message=message,
            payload=payload or {},
        )
    )
