import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


async def _create_user(session: AsyncSession, email: str, password: str) -> User:
    user = User(email=email, hashed_password=hash_password(password))
    session.add(user)
    await session.flush()
    return user


async def test_login_success(client, db_session: AsyncSession) -> None:
    await _create_user(db_session, "test@example.com", "secret123")
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client, db_session: AsyncSession) -> None:
    await _create_user(db_session, "user2@example.com", "correct")
    response = await client.post(
        "/api/v1/auth/login", json={"email": "user2@example.com", "password": "wrong"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


async def test_me_requires_auth(client) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_returns_current_user(client, db_session: AsyncSession) -> None:
    user = await _create_user(db_session, "me@example.com", "pass")
    token = create_access_token(user.id)
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_password_hashing() -> None:
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed)
    assert not verify_password("wrong", hashed)


def test_token_contains_user_id() -> None:
    uid = uuid.uuid4()
    token = create_access_token(uid)
    payload = decode_token(token)
    assert payload["sub"] == str(uid)
    assert payload["type"] == "access"


async def test_refresh_token_flow(client, db_session: AsyncSession) -> None:
    await _create_user(db_session, "refresh@example.com", "pass123")
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "pass123"},
    )
    refresh_token = login_resp.json()["refresh_token"]
    refresh_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()
