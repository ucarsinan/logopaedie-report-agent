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
            # I3 S-7: per-user Redis cutoff — if the user changed their
            # password (or otherwise revoked all access tokens) at or after
            # this token's `iat`, treat it as anonymous. Same fall-through as an
            # invalid JWT so existing 401 / required-auth paths behave
            # identically. Import lazily so middleware import doesn't pull
            # in the Redis client at module load.
            try:
                from dependencies import get_access_token_blocklist

                if get_access_token_blocklist().is_token_revoked(payload["sub"], int(payload["iat"])):
                    return await call_next(request)
            except Exception:
                # Redis outage must not break auth — fall open. Logged at
                # ERROR (not WARNING) so production monitoring catches
                # regressions in the blocklist code path. The fail-open
                # posture is deliberate: aggressive availability > tight
                # regression-detection here (an AttributeError bug silently
                # bypassing S-7 is acceptable for ~15min until access_token
                # expires; an auth-blocking 500 storm is not).
                logger.error("access_token_blocklist check failed; falling open", exc_info=True)
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
