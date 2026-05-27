"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/livez")
async def livez() -> dict[str, str]:
    """Public liveness probe.

    Unlike /health (guarded by the service token), this stays reachable without
    credentials so external load balancers and uptime monitors can confirm the
    process is up. It intentionally performs no dependency checks.
    """
    return {"status": "alive"}
