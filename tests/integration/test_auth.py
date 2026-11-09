"""Staff sign-in (email or mobile), session restore and token refresh. Customers don't sign in any more."""
import pytest

from app.common.enums import Role
from app.users import repository
from app.users.models import new_user
from tests.conftest import MANAGER


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def create_manager():
    await repository.insert(new_user(role=Role.MANAGER, name="Test Manager", email=MANAGER["email"],
                                     mobile=MANAGER["mobile"], password=MANAGER["password"]))


@pytest.mark.asyncio
@pytest.mark.parametrize("identifier", ["manager@test.com", "MANAGER@test.com", "9000000001", "+91 90000 00001"])
async def test_staff_can_sign_in_with_email_or_mobile(client, identifier):
    await create_manager()
    res = await client.post("/auth/login", json={"identifier": identifier, "password": MANAGER["password"]})

    assert res.status_code == 200
    body = res.json()
    assert body["accessToken"] and body["refreshToken"] and body["user"]["role"] == "manager"
    assert "passwordHash" not in body["user"]


@pytest.mark.asyncio
@pytest.mark.parametrize("identifier, password", [
    ("manager@test.com", "wrong-password"),
    ("nobody@example.com", "Manager@123"),
])
async def test_wrong_credentials_get_one_generic_error(client, identifier, password):
    await create_manager()
    res = await client.post("/auth/login", json={"identifier": identifier, "password": password})

    assert res.status_code == 401
    assert res.json()["error"] == {"code": "INVALID_CREDENTIALS", "message": "Incorrect email/mobile or password."}


@pytest.mark.asyncio
async def test_customer_sign_up_is_gone_and_old_customer_accounts_cannot_sign_in(client):
    assert (await client.post("/auth/register", json={})).status_code in (404, 405)

    await repository.insert(new_user(role=Role.CUSTOMER, name="Old Customer", email="old@example.com",
                                     mobile="9876543210", password="secret123"))
    res = await client.post("/auth/login", json={"identifier": "old@example.com", "password": "secret123"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CUSTOMER_LOGIN_DISABLED"


@pytest.mark.asyncio
async def test_me_returns_signed_in_user_and_requires_token(client, manager_headers):
    me = await client.get("/auth/me", headers=manager_headers)
    assert me.status_code == 200 and me.json()["email"] == "manager@test.com"

    assert (await client.get("/auth/me")).status_code == 401
    assert (await client.get("/auth/me", headers=auth("not-a-token"))).status_code == 401


@pytest.mark.asyncio
async def test_refresh_gives_new_tokens_and_rejects_access_token(client):
    await create_manager()
    tokens = (await client.post("/auth/login", json={"identifier": MANAGER["email"],
                                                     "password": MANAGER["password"]})).json()

    res = await client.post("/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    assert res.status_code == 200 and res.json()["accessToken"]

    wrong = await client.post("/auth/refresh", json={"refreshToken": tokens["accessToken"]})
    assert wrong.status_code == 401
