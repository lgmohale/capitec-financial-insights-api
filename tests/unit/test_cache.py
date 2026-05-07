from __future__ import annotations

import json

from app.core import cache


class FakeRedis:
    def __init__(self) -> None:
        self.values = {}
        self.ttls = {}
        self.deleted_keys = []

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.values[key] = value
        self.ttls[key] = ttl_seconds

    def delete(self, key: str) -> None:
        self.deleted_keys.append(key)
        self.values.pop(key, None)


def test_cache_helpers_use_json_serialization(monkeypatch) -> None:
    redis = FakeRedis()
    monkeypatch.setattr(cache, "get_redis_client", lambda: redis)

    cache.set_cache("aggregation:statement-id", {"total": 100})

    assert redis.ttls["aggregation:statement-id"] == cache.DEFAULT_TTL_SECONDS
    assert json.loads(redis.values["aggregation:statement-id"]) == {"total": 100}
    assert cache.get_cache("aggregation:statement-id") == {"total": 100}

    cache.delete_cache("aggregation:statement-id")

    assert redis.deleted_keys == ["aggregation:statement-id"]
    assert cache.get_cache("aggregation:statement-id") is None
