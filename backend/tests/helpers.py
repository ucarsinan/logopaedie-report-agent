"""Shared test utilities for auth integration tests."""

from __future__ import annotations

from sqlmodel import Session


def register_and_login(client, email: str, password: str) -> dict:
    client.post("/auth/register", json={"email": email, "password": password})
    token = next(t for _, to, t in client.email_svc.sent if to == email)
    client.post("/auth/verify-email", json={"token": token})
    client.email_svc.sent.clear()
    res = client.post("/auth/login", json={"email": email, "password": password})
    return res.json()


def auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def make_admin(client, email: str, password: str) -> dict:
    """Register + login, then elevate role to admin directly in the DB."""
    from sqlmodel import select

    from models.auth import User

    register_and_login(client, email, password)
    with Session(client.engine) as db:
        user = db.execute(select(User).where(User.email == email)).scalars().one()
        user.role = "admin"
        db.add(user)
        db.commit()
    # Re-login so the access token carries the admin role
    res = client.post("/auth/login", json={"email": email, "password": password})
    return res.json()
