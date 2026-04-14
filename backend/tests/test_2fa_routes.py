"""Tests for 2FA routes — setup, enable, disable, challenge login."""

from __future__ import annotations

# ── Helpers ───────────────────────────────────────────────────────────────────


def register_and_login(client, email: str, password: str) -> dict:
    client.post("/auth/register", json={"email": email, "password": password})
    from tests.helpers import verify_email_token

    verify_email_token(client, email)
    res = client.post("/auth/login", json={"email": email, "password": password})
    return res.json()


def auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def get_user(client, email: str):
    """Return the DB User object for the given email (direct DB query)."""
    import os
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from sqlmodel import Session, select

    from database import engine
    from models.auth import User

    with Session(engine) as db:
        return db.exec(select(User).where(User.email == email)).one()


# ── Task 4.3 ──────────────────────────────────────────────────────────────────


def test_get_challenge_store_dependency_resolves():
    from dependencies import get_challenge_store

    assert get_challenge_store() is not None
