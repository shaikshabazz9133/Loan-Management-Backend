"""Manager creates agents; agents then sign in with the credentials the manager set."""
import pytest

AGENT = {
    "name": "Ravi Kumar",
    "email": "ravi.agent@example.com",
    "mobile": "9000000011",
    "password": "agent123",
    "area": "Banjara Hills",
    "city": "Hyderabad",
    "location": {"lat": 17.4126, "lng": 78.4482},
    "active": True,
}


@pytest.mark.asyncio
async def test_manager_can_sign_in(client, manager_headers):
    me = await client.get("/auth/me", headers=manager_headers)
    assert me.json()["role"] == "manager"


@pytest.mark.asyncio
async def test_manager_creates_agent_and_agent_signs_in(client, manager_headers):
    res = await client.post("/agents", json=AGENT, headers=manager_headers)

    assert res.status_code == 201
    agent = res.json()
    assert agent["role"] == "agent"
    assert agent["employeeCode"] == "AG-1001"
    assert agent["location"] == {"lat": 17.4126, "lng": 78.4482}
    assert agent["area"] == "Banjara Hills" and agent["active"] is True

    login = await client.post("/auth/login", json={"identifier": AGENT["mobile"], "password": AGENT["password"]})
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "agent"


@pytest.mark.asyncio
async def test_agent_codes_increase_and_list_is_newest_first(client, manager_headers):
    await client.post("/agents", json=AGENT, headers=manager_headers)
    await client.post("/agents", json={**AGENT, "email": "priya@example.com", "mobile": "9000000012",
                                       "name": "Priya Sharma"}, headers=manager_headers)

    res = await client.get("/agents", headers=manager_headers)
    assert [a["employeeCode"] for a in res.json()] == ["AG-1002", "AG-1001"]


@pytest.mark.asyncio
async def test_inactive_agent_cannot_sign_in(client, manager_headers):
    await client.post("/agents", json={**AGENT, "active": False}, headers=manager_headers)

    res = await client.post("/auth/login", json={"identifier": AGENT["email"], "password": AGENT["password"]})
    assert res.status_code == 403
    assert res.json()["error"]["message"] == "Your agent account is deactivated. Please contact your manager."


@pytest.mark.asyncio
async def test_only_managers_can_create_agents(client, manager_headers):
    await client.post("/agents", json=AGENT, headers=manager_headers)
    login = await client.post("/auth/login", json={"identifier": AGENT["email"], "password": AGENT["password"]})
    headers = {"Authorization": f"Bearer {login.json()['accessToken']}"}

    other = {**AGENT, "email": "new@example.com", "mobile": "9000000099"}
    assert (await client.post("/agents", json=other, headers=headers)).status_code == 403
    assert (await client.post("/agents", json=other)).status_code == 401


@pytest.mark.asyncio
async def test_agent_email_must_be_unique_across_all_users(client, manager_headers):
    res = await client.post("/agents", json={**AGENT, "email": "manager@test.com"}, headers=manager_headers)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "EMAIL_TAKEN"


@pytest.mark.asyncio
async def test_agent_location_is_optional(client, manager_headers):
    res = await client.post("/agents", json={k: v for k, v in AGENT.items() if k != "location"}, headers=manager_headers)
    assert res.status_code == 201 and "location" not in res.json()


@pytest.mark.asyncio
async def test_agent_location_is_validated(client, manager_headers):
    res = await client.post("/agents", json={**AGENT, "location": {"lat": 200, "lng": 78.4}},
                            headers=manager_headers)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_manager_edits_agent_and_new_password_works(client, manager_headers):
    agent = (await client.post("/agents", json=AGENT, headers=manager_headers)).json()

    res = await client.patch(f"/agents/{agent['id']}", headers=manager_headers, json={
        "name": "Ravi K", "area": "Madhapur", "location": {"lat": 17.4483, "lng": 78.3915}, "password": "newpass1",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Ravi K" and body["area"] == "Madhapur"
    assert body["location"] == {"lat": 17.4483, "lng": 78.3915}
    assert body["email"] == AGENT["email"]  # untouched fields stay

    old = await client.post("/auth/login", json={"identifier": AGENT["email"], "password": AGENT["password"]})
    new = await client.post("/auth/login", json={"identifier": AGENT["email"], "password": "newpass1"})
    assert old.status_code == 401 and new.status_code == 200


@pytest.mark.asyncio
async def test_deactivating_agent_blocks_their_current_session(client, manager_headers):
    agent = (await client.post("/agents", json=AGENT, headers=manager_headers)).json()
    login = await client.post("/auth/login", json={"identifier": AGENT["email"], "password": AGENT["password"]})
    agent_headers = {"Authorization": f"Bearer {login.json()['accessToken']}"}

    await client.patch(f"/agents/{agent['id']}", json={"active": False}, headers=manager_headers)

    me = await client.get("/auth/me", headers=agent_headers)
    assert me.status_code == 403 and me.json()["error"]["code"] == "ACCOUNT_INACTIVE"


@pytest.mark.asyncio
async def test_agent_can_keep_own_email_but_not_take_another(client, manager_headers):
    agent = (await client.post("/agents", json=AGENT, headers=manager_headers)).json()

    same = await client.patch(f"/agents/{agent['id']}", json={"email": AGENT["email"]}, headers=manager_headers)
    taken = await client.patch(f"/agents/{agent['id']}", json={"email": "manager@test.com"}, headers=manager_headers)
    assert same.status_code == 200
    assert taken.status_code == 409 and taken.json()["error"]["code"] == "EMAIL_TAKEN"


@pytest.mark.asyncio
async def test_manager_deletes_agent(client, manager_headers):
    agent = (await client.post("/agents", json=AGENT, headers=manager_headers)).json()

    assert (await client.delete(f"/agents/{agent['id']}", headers=manager_headers)).status_code == 204
    assert (await client.get("/agents", headers=manager_headers)).json() == []
    missing = await client.patch(f"/agents/{agent['id']}", json={"active": True}, headers=manager_headers)
    assert missing.status_code == 404
