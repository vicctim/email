from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import get_settings


def app_timezone() -> ZoneInfo:
    timezone_name = get_settings().app_timezone
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/Sao_Paulo")


def local_day_bounds_utc(reference: datetime | None = None) -> tuple[datetime, datetime]:
    tz = app_timezone()
    now = reference or datetime.now(timezone.utc)
    local_now = now.astimezone(tz)
    local_start = datetime.combine(local_now.date(), time.min, tzinfo=tz)
    local_end = local_start + timedelta(days=1)
    return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)


def local_tz() -> ZoneInfo:
    return app_timezone()
