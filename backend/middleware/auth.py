"""Auth middleware (JWT)."""

from __future__ import annotations

import logging
import os

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Non-throwing JWT middleware — populates request.state.user or sets it to None."""

    SKIP_PREFIXES = ("/health", "/cron/")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.user = None
        if request.method == "OPTIONS" or request.url.path.startswith(self.SKIP_PREFIXES):
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return await call_next(request)
        token = auth.split(" ", 1)[1].strip()

        import jwt as _jwt

        secret = os.environ.get("JWT_SECRET")
        if not secret or not token:
            return await call_next(request)
        try:
            payload = _jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"require": ["exp", "iat", "sub"]},
            )
            if payload.get("type") != "access":
                return await call_next(request)
            session_hash = payload.get("sid")
            request.state.user = {
                "id": payload["sub"],
                "role": payload.get("role", "user"),
                "sid": session_hash,
            }
            request.state.session_hash = session_hash  # refresh_token_hash of the issuing session
        except _jwt.InvalidTokenError:
            request.state.user = None
        return await call_next(request)
