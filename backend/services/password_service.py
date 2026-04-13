"""Argon2id password hashing wrapper around passlib."""

from __future__ import annotations

from functools import cached_property

from passlib.context import CryptContext
from passlib.exc import UnknownHashError


class PasswordService:
    def __init__(self) -> None:
        self._ctx = CryptContext(
            schemes=["argon2"],
            deprecated="auto",
            argon2__time_cost=3,
            argon2__memory_cost=65536,
            argon2__parallelism=1,
        )

    @cached_property
    def dummy_hash(self) -> str:
        """Stable argon2 hash used by auth_service as a sentinel to equalise
        timing on the 'user not found' path and prevent user-enumeration
        timing oracles. Computed once per process."""
        return self._ctx.hash("dummy-password-for-timing-equalization")

    def hash(self, password: str) -> str:
        return self._ctx.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        if not password_hash or not password_hash.startswith("$argon2"):
            return False
        try:
            return self._ctx.verify(password, password_hash)
        except (ValueError, UnknownHashError):
            return False
