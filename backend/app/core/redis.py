from redis.asyncio import Redis, from_url

from app.core.config import get_settings

_client: Redis | None = None


def get_redis() -> Redis:
    """Return the shared async Redis client; lifecycle ownership is in app lifespan."""
    global _client
    if _client is None:
        _client = from_url(get_settings().redis_url, encoding="utf-8", decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
