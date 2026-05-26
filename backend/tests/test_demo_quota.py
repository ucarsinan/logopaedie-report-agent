"""H-2: anonymous demo usage of the expensive AI endpoints must be capped per
client per day, so an unauthenticated visitor cannot burn unlimited Groq credits.
"""

from __future__ import annotations


class FakeRedis:
    """Minimal in-memory stand-in for the incr/expire calls the quota uses."""

    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds


def test_within_quota_until_limit(monkeypatch):
    from services import demo_quota

    monkeypatch.setenv("DEMO_DAILY_LIMIT", "3")
    redis = FakeRedis()
    results = [demo_quota.within_demo_quota("1.2.3.4", redis) for _ in range(4)]
    assert results == [True, True, True, False]


def test_sets_expiry_on_first_increment(monkeypatch):
    from services import demo_quota

    monkeypatch.setenv("DEMO_DAILY_LIMIT", "5")
    redis = FakeRedis()
    demo_quota.within_demo_quota("9.9.9.9", redis)
    # exactly one key, with a ~24h TTL set on first hit
    assert len(redis.expirations) == 1
    assert next(iter(redis.expirations.values())) == 24 * 60 * 60


def test_quota_is_per_identifier(monkeypatch):
    from services import demo_quota

    monkeypatch.setenv("DEMO_DAILY_LIMIT", "1")
    redis = FakeRedis()
    assert demo_quota.within_demo_quota("ip-a", redis) is True
    assert demo_quota.within_demo_quota("ip-a", redis) is False
    # a different client still has its own fresh budget
    assert demo_quota.within_demo_quota("ip-b", redis) is True


def test_anonymous_generate_blocked_after_daily_limit(client, session_id, mock_groq, mock_redis, monkeypatch):
    """Route-level: an anonymous demo session is cut off once the daily cap is hit."""
    monkeypatch.setenv("DEMO_DAILY_LIMIT", "1")
    mock_groq["json"].return_value = {"report_type": "befundbericht", "anamnese": "", "befund": ""}

    # Give the mocked Redis a real counter so the quota actually accumulates.
    counters: dict[str, int] = {}

    def fake_incr(key):
        counters[key] = counters.get(key, 0) + 1
        return counters[key]

    mock_redis.incr = fake_incr
    mock_redis.expire = lambda key, seconds: None

    first = client.post(f"/sessions/{session_id}/generate")
    second = client.post(f"/sessions/{session_id}/generate")
    assert first.status_code == 200
    assert second.status_code == 429
