"""Customer sign-up, sign-in (email or mobile), session restore and token refresh."""
import pytest

CUSTOMER = {
    "name": "Aarav Mehta",
    "email": "Aarav@Example.com",
    "mobile": "98765 43210",
    "password": "secret123",
    "termsAccepted": True,
}


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_customer_signup_returns_tokens_and_customer(client):
    res = await client.post("/auth/register", json=CUSTOMER)

    assert res.status_code == 201
    body = res.json()
    assert body["accessToken"] and body["refreshToken"] and body["tokenType"] == "bearer"
    user = body["user"]
    assert user["role"] == "customer"
    assert user["email"] == "aarav@example.com"  # stored lowercase
    assert user["mobile"] == "9876543210"  # spaces removed
    assert "passwordHash" not in user and "password" not in user


@pytest.mark.asyncio
@pytest.mark.parametrize("change, code", [
    ({"mobile": "9999999999"}, "EMAIL_TAKEN"),
    ({"email": "other@example.com"}, "MOBILE_TAKEN"),
])
async def test_signup_rejects_duplicate_email_or_mobile(client, change, code):
    await client.post("/auth/register", json=CUSTOMER)
    res = await client.post("/auth/register", json={**CUSTOMER, **change})

    assert res.status_code == 409
    assert res.json()["error"]["code"] == code


@pytest.mark.asyncio
async def test_signup_validation_errors_are_per_field(client):
    res = await client.post("/auth/register", json={**CUSTOMER, "mobile": "12345", "password": "short",
                                                     "termsAccepted": False})

    assert res.status_code == 422
    error = res.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]["mobile"] == "Enter a valid 10-digit mobile number."
    assert error["details"]["termsAccepted"] == "You must accept the terms and conditions."
    assert "password" in error["details"]


@pytest.mark.asyncio
@pytest.mark.parametrize("identifier", ["aarav@example.com", "AARAV@example.com", "9876543210", "+91 98765 43210"])
async def test_customer_can_sign_in_with_email_or_mobile(client, identifier):
    await client.post("/auth/register", json=CUSTOMER)
    res = await client.post("/auth/login", json={"identifier": identifier, "password": "secret123"})

    assert res.status_code == 200
    assert res.json()["user"]["role"] == "customer"


@pytest.mark.asyncio
@pytest.mark.parametrize("identifier, password", [
    ("aarav@example.com", "wrong-password"),
    ("nobody@example.com", "secret123"),
])
async def test_wrong_credentials_get_one_generic_error(client, identifier, password):
    await client.post("/auth/register", json=CUSTOMER)
    res = await client.post("/auth/login", json={"identifier": identifier, "password": password})

    assert res.status_code == 401
    assert res.json()["error"] == {"code": "INVALID_CREDENTIALS", "message": "Incorrect email/mobile or password."}


@pytest.mark.asyncio
async def test_me_returns_signed_in_user_and_requires_token(client):
    tokens = (await client.post("/auth/register", json=CUSTOMER)).json()

    me = await client.get("/auth/me", headers=auth(tokens["accessToken"]))
    assert me.status_code == 200 and me.json()["email"] == "aarav@example.com"

    assert (await client.get("/auth/me")).status_code == 401
    assert (await client.get("/auth/me", headers=auth("not-a-token"))).status_code == 401


@pytest.mark.asyncio
async def test_refresh_gives_new_tokens_and_rejects_access_token(client):
    tokens = (await client.post("/auth/register", json=CUSTOMER)).json()

    res = await client.post("/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    assert res.status_code == 200 and res.json()["accessToken"]

    wrong = await client.post("/auth/refresh", json={"refreshToken": tokens["accessToken"]})
    assert wrong.status_code == 401
