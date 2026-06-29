"""Per-user access-token revocation via Redis cutoff timestamps.

When a user changes their password (or another action invalidates their
active access tokens), we SETEX a "revoked_until" key with the current
unix timestamp and a TTL equal to the access-token lifetime. The auth
dependency compares each incoming token's ``iat`` claim against this
cutoff and rejects tokens issued at or before it. After the TTL expires, the
key disappears and no comparison is needed (tokens older than the TTL
are already expired by JWT validation).

I3 S-7: closes the gap where short-lived access tokens issued before a
password change remained valid until natural expiry. Combined with the
optimistic ``get_optional_user`` (which skips the per-request User DB
fetch) this gave a stolen access token up to ``access_token_ttl``
survival after the user changed their password.

Approach (b) — chosen over per-jti tracking:
- No new JWT claim (no ``jti``).
- One Redis GET per authenticated request (comparable to the trade-off
  the session optimization in ``c0980ab`` made the other way).
- Key auto-expires; no GC needed.
"""

from __future__ import annotations

import time
from typing import Protocol


class _RedisLike(Protocol):
    def setex(self, name: str, time: int, value: str) -> object: ...
    def get(self, name: str) -> object: ...


class AccessTokenBlocklist:
    """Redis-backed per-user access-token revocation cutoff."""

    PREFIX = "access_token_revoked_until:"

    def __init__(self, redis_client: _RedisLike, ttl_seconds: int) -> None:
        self._r = redis_client
        self._ttl = ttl_seconds

    @classmethod
    def _key(cls, user_id: str) -> str:
        return f"{cls.PREFIX}{user_id}"

    def revoke_all_for_user(self, user_id: str) -> None:
        """Set the revocation cutoff to NOW.

        All access tokens for this user with ``iat <= now`` are subsequently
        rejected. TTL == access token lifetime, so the key disappears once
        it can no longer block any non-expired token.
        """
        self._r.setex(self._key(user_id), self._ttl, str(int(time.time())))

    def is_token_revoked(self, user_id: str, token_iat: int) -> bool:
        """Check whether a token with ``iat`` claim is revoked for this user.

        Returns ``False`` if no cutoff is set (the common case — one Redis
        GET, no further work). On a garbled cutoff value we fail open
        (return ``False``) rather than 500'ing every authenticated request.
        """
        raw = self._r.get(self._key(user_id))
        if raw is None:
            return False
        if isinstance(raw, bytes):
            try:
                raw_str: str = raw.decode("utf-8")
            except UnicodeDecodeError:
                return False
        elif isinstance(raw, str):
            raw_str = raw
        else:
            return False
        try:
            cutoff = int(raw_str)
        except (TypeError, ValueError):
            return False
        return token_iat <= cutoff
