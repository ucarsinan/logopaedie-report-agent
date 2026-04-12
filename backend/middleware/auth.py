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

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        api_key = os.environ.get("API_KEY")

        # Auth disabled if no API_KEY configured
        if not api_key:
            return await call_next(request)

        # Skip auth for health check and CORS preflight
        if request.url.path == "/health" or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("Missing or malformed Authorization header from %s", request.client.host if request.client else "unknown")
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header required. Format: 'Bearer <API_KEY>'"},
            )

        token = auth_header[len("Bearer "):]
        if token != api_key:
            logger.warning("Invalid API key from %s", request.client.host if request.client else "unknown")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key."},
            )

        return await call_next(request)
