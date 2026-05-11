import asyncio
import os
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient


os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin")
os.environ.setdefault("IMAP_LISTENER_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://emailext:emailext_dev_123@127.0.0.1:5434/emailext",
    ),
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.connection import engine, session_factory  # noqa: E402
from app.database.models import Base  # noqa: E402
from app.main import app  # noqa: E402


async def _prepare_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@pytest.fixture
def ensure_db() -> None:
    try:
        asyncio.run(_prepare_database())
    except Exception as exc:
        pytest.skip(f"Banco de teste indisponível: {exc}")


@pytest_asyncio.fixture
async def db_session(ensure_db) -> AsyncIterator:
    async with session_factory() as session:
        yield session


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient, ensure_db) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
