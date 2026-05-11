import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings
from app.security import decode_access_token


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.settings = get_settings()
        self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True)
        self.memory_hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self.settings.rate_limit_enabled:
            return await call_next(request)

        rule = self._rule_for(request)
        if rule is None:
            return await call_next(request)

        bucket, limit = rule
        allowed, retry_after = await self._is_allowed(bucket, limit)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit excedido"},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)

    def _rule_for(self, request: Request) -> tuple[str, int] | None:
        path = request.url.path.rstrip("/")
        if path == "/api/auth/login" and request.method.upper() == "POST":
            return (
                f"auth-login:{self._client_id(request)}",
                self.settings.auth_login_rate_limit_per_minute,
            )
        if path.startswith("/api/"):
            return (
                f"api:{self._authenticated_id(request)}",
                self.settings.authenticated_rate_limit_per_minute,
            )
        return None

    async def _is_allowed(self, bucket: str, limit: int) -> tuple[bool, int]:
        key = f"rate-limit:{bucket}:{int(time.time() // 60)}"
        try:
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, 70)
            return count <= limit, 60
        except Exception:
            return self._memory_is_allowed(bucket, limit)

    def _memory_is_allowed(self, bucket: str, limit: int) -> tuple[bool, int]:
        now = time.monotonic()
        window_start = now - 60
        hits = self.memory_hits[bucket]
        while hits and hits[0] < window_start:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = max(1, int(60 - (now - hits[0])))
            return False, retry_after
        hits.append(now)
        return True, 60

    @staticmethod
    def _client_id(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
        return request.client.host if request.client else "unknown"

    def _authenticated_id(self, request: Request) -> str:
        auth = request.headers.get("authorization", "")
        scheme, _, token = auth.partition(" ")
        if scheme.lower() == "bearer" and token:
            subject = decode_access_token(token)
            if subject:
                return f"user:{subject}"
        return f"ip:{self._client_id(request)}"

