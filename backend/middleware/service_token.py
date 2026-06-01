"""Service-token middleware: guards /health and /cron/* paths."""

from __future__ import annotations

import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


def _is_production() -> bool:
    """Same env contract as ``rate_limiter._is_production``."""
    return os.environ.get("VERCEL_ENV") == "production" or os.environ.get("ENV") == "production"


class ServiceTokenMiddleware(BaseHTTPMiddleware):
    GUARDED_PREFIXES = ("/health", "/cron/")

    def __init__(self, app: ASGIApp) -> None:
        # Fail boot in production rather than silently exposing /health.
        # SERVICE_TOKEN unset = "dev mode, skip the check" — only safe outside prod.
        if _is_production() and not os.getenv("SERVICE_TOKEN"):
            raise RuntimeError("SERVICE_TOKEN must be set when VERCEL_ENV/ENV=production")
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if not path.startswith(self.GUARDED_PREFIXES):
            return await call_next(request)

        expected = os.getenv("SERVICE_TOKEN")
        if not expected:
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        # S-5: constant-time compare to avoid timing side-channels on the
        # server-issued shared secret. Practical impact is low (Vercel TLS,
        # short token), but principle-of-least-surprise: every shared-secret
        # bearer compare in this codebase uses hmac.compare_digest.
        if not hmac.compare_digest(auth, f"Bearer {expected}"):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)
