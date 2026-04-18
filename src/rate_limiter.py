import asyncio

from fastapi import HTTPException, Request, status
from limits import parse
from limits.storage import MemoryStorage, RedisStorage
from limits.strategies import MovingWindowRateLimiter

from src.internal.settings import settings

_storage = RedisStorage(settings.redis_url) if settings.redis_url else MemoryStorage()
_limiter = MovingWindowRateLimiter(_storage)
_rate = parse(settings.exec_rate_limit)


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


async def require_rate_limit(request: Request) -> None:
    ip = _client_ip(request)
    try:
        allowed = await asyncio.to_thread(_limiter.hit, _rate, ip)
    except Exception:
        # Redis unavailable — fail open rather than blocking all requests.
        return
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Allowed: {settings.exec_rate_limit}.",
        )
