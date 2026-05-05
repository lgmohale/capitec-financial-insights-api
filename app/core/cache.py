from __future__ import annotations

import json
from typing import Any

from redis import Redis

from app.config import get_settings

DEFAULT_TTL_SECONDS = 3600


def get_redis_client() -> Redis:
    return Redis.from_url(
        get_settings().redis_url,
        decode_responses=True,
    )


def get_cache(key: str) -> Any | None:
    cached_value = get_redis_client().get(key)
    if cached_value is None:
        return None

    return json.loads(cached_value)


def set_cache(
    key: str,
    value: Any,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> None:
    get_redis_client().setex(
        key,
        ttl_seconds,
        json.dumps(value),
    )


def delete_cache(key: str) -> None:
    get_redis_client().delete(key)
