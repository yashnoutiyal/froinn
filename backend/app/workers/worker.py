"""ARQ worker configuration. Register real jobs here as modules are introduced."""

from typing import ClassVar

from arq.connections import RedisSettings

from app.core.config import get_settings


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    redis_settings = redis_settings()
    functions: ClassVar[list] = []
