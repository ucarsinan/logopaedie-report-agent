"""API key authentication middleware."""

from __future__ import annotations

import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger(__name__)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Require Bearer token authentication if API_KEY env var is set.

    Skips authentication for:
    - /health endpoint
    - OPTIONS requests (CORS preflight)
    - When API_KEY is not configured (local dev)
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        api_key = os.environ.get("API_KEY")

        # Auth disabled if no API_KEY configured
        if not api_key:
            return await call_next(request)

        # Skip auth for health check and CORS preflight
        if request.url.path == "/health" or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning(
                "Missing or malformed Authorization header from %s",
                request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header required. Format: 'Bearer <API_KEY>'"},
            )

        token = auth_header[len("Bearer ") :]
        if token != api_key:
            logger.warning("Invalid API key from %s", request.client.host if request.client else "unknown")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key."},
            )

        return await call_next(request)


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
            request.state.user = {
                "id": payload["sub"],
                "role": payload.get("role", "user"),
                "sid": payload.get("sid"),
            }
        except _jwt.InvalidTokenError:
            request.state.user = None
        return await call_next(request)
