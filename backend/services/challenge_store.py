"""Redis-backed single-use challenge store for 2FA login flow."""

from __future__ import annotations

from typing import Protocol


class RedisLike(Protocol):
    def set(self, name: str, value: str, ex: int | None = ..., nx: bool = ...) -> bool | None: ...
    def execute_command(self, *args: object) -> object: ...


class ChallengeStore:
    """Stores short-lived 2FA challenge_id -> user_id mappings.

    consume() is atomic (GETDEL) so concurrent callers cannot both succeed.
    """

    PREFIX = "auth:2fa:challenge:"

    def __init__(self, client: RedisLike) -> None:
        self._client = client

    def put(self, challenge_id: str, user_id: str, ttl_seconds: int = 300) -> None:
        self._client.set(self._key(challenge_id), user_id, ex=ttl_seconds, nx=True)

    def consume(self, challenge_id: str) -> str | None:
        raw = self._client.execute_command("GETDEL", self._key(challenge_id))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            return raw.decode("utf-8")
        return str(raw)

    def _key(self, challenge_id: str) -> str:
        return f"{self.PREFIX}{challenge_id}"
