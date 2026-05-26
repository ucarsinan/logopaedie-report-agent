"""Per-client daily quota for anonymous demo usage of the expensive AI endpoints.

Anonymous demo sessions are intentionally usable without login (portfolio
showcase), but that means an unauthenticated visitor could otherwise trigger
unbounded Groq calls. This caps demo calls per client per day, backed by the
same Upstash Redis the session store uses, so the limit is shared across
serverless instances.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

_KEY_PREFIX = "demoquota:"
_DAY_SECONDS = 24 * 60 * 60


def demo_daily_limit() -> int:
    return int(os.getenv("DEMO_DAILY_LIMIT", "20"))


def _key(identifier: str) -> str:
    today = datetime.now(UTC).date().isoformat()
    return f"{_KEY_PREFIX}{today}:{identifier}"


def within_demo_quota(identifier: str, redis) -> bool:
    """Increment the client's daily demo counter; True while still within the limit.

    The counter key carries the date and expires after 24h, so each client gets a
    fresh budget per day without a separate reset job.
    """
    key = _key(identifier)
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, _DAY_SECONDS)
    return count <= demo_daily_limit()
