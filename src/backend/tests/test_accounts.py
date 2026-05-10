import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.account import seed_skr_for_mandant
from app.services.auth import create_access_token, hash_password


async def _setup(session: AsyncSession) -> dict[str, str]:
    user = User(email=f"a{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(name="Accts GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")
    token = create_access_token(user.id, mandant.id)
    return {"Authorization": f"Bearer {token}"}


async def test_list_accounts_returns_seeded_data(
    client, db_session: AsyncSession
) -> None:
    headers = await _setup(db_session)
    resp = await client.get("/api/v1/accounts", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) > 0


async def test_seed_account_only_allows_private_share_edit(
    client, db_session: AsyncSession
) -> None:
    headers = await _setup(db_session)
    accounts = (await client.get("/api/v1/accounts", headers=headers)).json()
    seed_id = accounts[0]["id"]
    resp = await client.patch(
        f"/api/v1/accounts/{seed_id}",
        json={"private_share_percent": 20},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["private_share_percent"] == 20
    resp = await client.patch(
        f"/api/v1/accounts/{seed_id}", json={"name": "Hacked"}, headers=headers
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "ACCOUNT_NOT_EDITABLE"


async def test_create_custom_account(client, db_session: AsyncSession) -> None:
    headers = await _setup(db_session)
    resp = await client.post(
        "/api/v1/accounts",
        json={"account_number": "9999", "name": "Test Custom", "account_class": "9xxx"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["is_custom"] is True


async def test_account_isolation(client, db_session: AsyncSession) -> None:
    headers1 = await _setup(db_session)
    headers2 = await _setup(db_session)
    accounts1 = (await client.get("/api/v1/accounts", headers=headers1)).json()
    accounts2 = (await client.get("/api/v1/accounts", headers=headers2)).json()
    ids1 = {a["id"] for a in accounts1}
    ids2 = {a["id"] for a in accounts2}
    assert ids1.isdisjoint(ids2), "Accounts from different mandants must not overlap"


async def test_delete_custom_account(client, db_session: AsyncSession) -> None:
    headers = await _setup(db_session)
    create_resp = await client.post(
        "/api/v1/accounts",
        json={"account_number": "8888", "name": "To Delete", "account_class": "8xxx"},
        headers=headers,
    )
    account_id = create_resp.json()["id"]
    del_resp = await client.delete(f"/api/v1/accounts/{account_id}", headers=headers)
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/api/v1/accounts/{account_id}", headers=headers)
    assert get_resp.json()["is_active"] is False


async def test_delete_seed_account_fails(client, db_session: AsyncSession) -> None:
    headers = await _setup(db_session)
    accounts = (await client.get("/api/v1/accounts", headers=headers)).json()
    seed_id = accounts[0]["id"]
    resp = await client.delete(f"/api/v1/accounts/{seed_id}", headers=headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "ACCOUNT_NOT_EDITABLE"
