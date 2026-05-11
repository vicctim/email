import json
from pathlib import Path
from typing import Any

from app.config import get_settings


def default_global_settings() -> dict[str, Any]:
    settings = get_settings()
    return {
        "default_publish_delay": settings.default_publish_delay,
        "polling_interval_seconds": 60,
        "notifications_enabled": bool(settings.evolution_api_url and settings.evolution_api_key),
        "whatsapp_notify_number": settings.whatsapp_notify_number,
    }


def _settings_path() -> Path:
    path = Path(get_settings().settings_storage_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def read_global_settings() -> dict[str, Any]:
    data = default_global_settings()
    path = _settings_path()
    if not path.exists():
        return data
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return data
    if isinstance(stored, dict):
        data.update(stored)
    return data


def update_global_settings(values: dict[str, Any]) -> dict[str, Any]:
    data = read_global_settings()
    data.update({key: value for key, value in values.items() if value is not None})
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data

