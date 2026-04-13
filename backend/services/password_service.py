"""Argon2id password hashing wrapper around passlib."""

from __future__ import annotations

from passlib.context import CryptContext
from passlib.exc import UnknownHashError


class PasswordService:
    def __init__(self) -> None:
        self._ctx = CryptContext(
            schemes=["argon2"],
            deprecated="auto",
            argon2__time_cost=3,
            argon2__memory_cost=65536,
            argon2__parallelism=4,
        )

    def hash(self, password: str) -> str:
        return self._ctx.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        if not password_hash or not password_hash.startswith("$argon2"):
            return False
        try:
            return self._ctx.verify(password, password_hash)
        except (ValueError, UnknownHashError):
            return False
