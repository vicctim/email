import asyncio
from contextlib import asynccontextmanager
from contextlib import suppress
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.rate_limit import RateLimitMiddleware
from app.api.routes import accounts, auth, dashboard, logs, plugin, queue, rules, settings as settings_routes, sites
from app.config import get_settings
from app.database.connection import dispose_engine
from app.services.imap_listener import ImapListener


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    listener_task: asyncio.Task | None = None
    listener: ImapListener | None = None
    if settings.imap_listener_enabled:
        listener = ImapListener()
        listener_task = asyncio.create_task(listener.run_forever())
    yield
    if listener:
        listener.stop()
    if listener_task:
        listener_task.cancel()
        with suppress(asyncio.CancelledError):
            await listener_task
    await dispose_engine()


app = FastAPI(
    title="Email Content Extractor API",
    version="0.1.0",
    debug=settings.app_debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(auth.router)
app.include_router(sites.router)
app.include_router(accounts.router)
app.include_router(rules.router)
app.include_router(queue.router)
app.include_router(logs.router)
app.include_router(dashboard.router)
app.include_router(settings_routes.router)
app.include_router(plugin.router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "email-content-extractor",
        "environment": settings.app_env,
    }
