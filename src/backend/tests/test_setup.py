"""Tests for the /api/v1/setup endpoints (first-admin bootstrap)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth import decode_token


_VALID_SETUP_PAYLOAD = {
    "email": "admin@example.com",
    "password": "securepass",
    "mandant_name": "Test GmbH",
    "skr_variant": "skr03",
}


async def test_setup_status_needs_bootstrap(client: AsyncClient) -> None:
    """Fresh (empty) DB reports that bootstrap is required."""
    response = await client.get("/api/v1/setup/status")
    assert response.status_code == 200
    assert response.json() == {"needs_setup": True}


async def test_setup_status_after_setup(client: AsyncClient) -> None:
    """After a successful POST /setup the status endpoint reports no setup needed."""
    post_resp = await client.post("/api/v1/setup", json=_VALID_SETUP_PAYLOAD)
    assert post_resp.status_code == 200

    get_resp = await client.get("/api/v1/setup/status")
    assert get_resp.status_code == 200
    assert get_resp.json() == {"needs_setup": False}


async def test_post_setup_creates_user_and_mandant(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """POST /setup creates exactly one user and one mandant in the database."""
    from sqlalchemy import func, select

    from app.models.mandant import Mandant
    from app.models.user import User

    response = await client.post("/api/v1/setup", json=_VALID_SETUP_PAYLOAD)
    assert response.status_code == 200

    user_count = (
        await db_session.execute(select(func.count()).select_from(User))
    ).scalar_one()
    assert user_count == 1

    mandant_count = (
        await db_session.execute(select(func.count()).select_from(Mandant))
    ).scalar_one()
    assert mandant_count == 1


async def test_post_setup_returns_valid_token(client: AsyncClient) -> None:
    """POST /setup returns a JWT that can be decoded and contains the user's sub."""
    response = await client.post("/api/v1/setup", json=_VALID_SETUP_PAYLOAD)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

    # Decode the access token — decode_token raises on invalid tokens.
    payload = decode_token(data["access_token"])
    assert payload.get("type") == "access"
    assert "sub" in payload


async def test_post_setup_idempotent_returns_404(client: AsyncClient) -> None:
    """A second call to POST /setup returns 404 (setup already completed)."""
    first = await client.post("/api/v1/setup", json=_VALID_SETUP_PAYLOAD)
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/setup",
        json={**_VALID_SETUP_PAYLOAD, "email": "other@example.com"},
    )
    assert second.status_code == 404


async def test_post_setup_password_too_short(client: AsyncClient) -> None:
    """A password shorter than 8 characters is rejected with 422."""
    payload = {**_VALID_SETUP_PAYLOAD, "password": "short7"}  # 6 chars
    response = await client.post("/api/v1/setup", json=payload)
    assert response.status_code == 422
