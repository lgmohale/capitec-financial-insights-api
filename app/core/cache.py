from __future__ import annotations

import json
from typing import Any

from redis import Redis

from app.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import CACHE_HITS, CACHE_MISSES

DEFAULT_TTL_SECONDS = 3600
logger = get_logger(__name__)


def get_redis_client() -> Redis:
    return Redis.from_url(
        get_settings().redis_url,
        decode_responses=True,
    )


def get_cache(key: str) -> Any | None:
    cached_value = get_redis_client().get(key)
    event = cache_event_name(key)
    if cached_value is None:
        CACHE_MISSES.labels(event).inc()
        logger.info(
            "Cache miss",
            extra={"event_name": "cache_miss"},
        )
        return None

    CACHE_HITS.labels(event).inc()
    logger.info(
        "Cache hit",
        extra={"event_name": "cache_hit"},
    )
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


def cache_event_name(key: str) -> str:
    return key.split(":", maxsplit=1)[0]
