import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.auth import create_access_token, decode_token, hash_password


async def _setup_user_and_mandant(session: AsyncSession) -> tuple[User, Mandant]:
    user = User(email=f"u{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    await session.flush()
    mandant = Mandant(name="Test GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    link = UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin")
    session.add(link)
    await session.flush()
    return user, mandant


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def test_create_mandant(client, db_session: AsyncSession) -> None:
    user = User(email=f"c{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    db_session.add(user)
    await db_session.flush()
    resp = await client.post(
        "/api/v1/mandants",
        json={"name": "New GmbH", "skr_variant": "skr03"},
        headers=_auth(user),
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "New GmbH"


async def test_list_mandants_only_own(client, db_session: AsyncSession) -> None:
    user, mandant = await _setup_user_and_mandant(db_session)
    resp = await client.get("/api/v1/mandants", headers=_auth(user))
    assert resp.status_code == 200
    ids = [m["id"] for m in resp.json()]
    assert str(mandant.id) in ids


async def test_switch_mandant_issues_scoped_token(
    client, db_session: AsyncSession
) -> None:
    user, mandant = await _setup_user_and_mandant(db_session)
    resp = await client.post(
        f"/api/v1/mandants/{mandant.id}/switch", headers=_auth(user)
    )
    assert resp.status_code == 200
    payload = decode_token(resp.json()["access_token"])
    assert payload["mandant_id"] == str(mandant.id)


async def test_cannot_access_other_users_mandant(
    client, db_session: AsyncSession
) -> None:
    _, mandant = await _setup_user_and_mandant(db_session)
    other_user = User(
        email=f"o{uuid.uuid4()}@x.com", hashed_password=hash_password("pw")
    )
    db_session.add(other_user)
    await db_session.flush()
    resp = await client.get(f"/api/v1/mandants/{mandant.id}", headers=_auth(other_user))
    assert resp.status_code == 404


async def test_mandant_isolation_cross_user(client, db_session: AsyncSession) -> None:
    user1, mandant1 = await _setup_user_and_mandant(db_session)
    user2, _ = await _setup_user_and_mandant(db_session)
    resp = await client.patch(
        f"/api/v1/mandants/{mandant1.id}",
        json={"name": "Hacked GmbH"},
        headers=_auth(user2),
    )
    assert resp.status_code == 404
