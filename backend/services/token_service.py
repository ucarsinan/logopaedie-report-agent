"""JWT access tokens and opaque refresh tokens."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import InvalidTokenError


class TokenService:
    def __init__(self) -> None:
        secret = os.getenv("JWT_SECRET")
        if not secret:
            raise RuntimeError("JWT_SECRET env var is required")
        self._secret = secret
        self._alg = "HS256"
        self._access_ttl = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "15")))
        self._leeway = int(os.getenv("JWT_LEEWAY_SECONDS", "0"))

    def encode_access(self, user_id: UUID, session_id: UUID | None = None) -> str:
        now = datetime.now(UTC)
        payload: dict = {
            "sub": str(user_id),
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + self._access_ttl).timestamp()),
        }
        if session_id is not None:
            payload["sid"] = str(session_id)
        return jwt.encode(payload, self._secret, algorithm=self._alg)

    def decode_access(self, token: str) -> dict:
        payload = jwt.decode(
            token,
            self._secret,
            algorithms=[self._alg],
            options={"require": ["exp", "iat", "sub"]},
            leeway=self._leeway,
        )
        if payload.get("type") != "access":
            raise InvalidTokenError("Token type mismatch")
        sub = payload.get("sub")
        if not isinstance(sub, str) or not sub:
            raise InvalidTokenError("Missing or invalid 'sub' claim")
        try:
            UUID(sub)
        except (TypeError, ValueError) as exc:
            raise InvalidTokenError("'sub' is not a valid UUID") from exc
        return payload

    def encode_refresh(self) -> tuple[str, str]:
        plain = secrets.token_urlsafe(32)
        return plain, self.hash_refresh(plain)

    def hash_refresh(self, plaintext: str) -> str:
        return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
