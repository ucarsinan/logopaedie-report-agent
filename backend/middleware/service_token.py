"""Service-token middleware: guards /health and /cron/* paths."""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class ServiceTokenMiddleware(BaseHTTPMiddleware):
    GUARDED_PREFIXES = ("/health", "/cron/")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if not path.startswith(self.GUARDED_PREFIXES):
            return await call_next(request)

        expected = os.getenv("SERVICE_TOKEN")
        if not expected:
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if auth != f"Bearer {expected}":
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)
