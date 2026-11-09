"""Customer submits a loan application (form + documents in one request); each role sees the right list."""
import json
from datetime import date

import pytest

PDF = b"%PDF-1.4 test document"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32

CUSTOMER = {"name": "Usman Khan", "email": "usman@example.com", "mobile": "9898989898",
            "password": "Test@1234", "termsAccepted": True}
NEAR = {"lat": 17.4152, "lng": 78.4421}  # Banjara Hills
FAR = {"lat": 17.4058, "lng": 78.5591}  # Uppal, ~12 km away
AGENT = {"name": "Ravi Kumar", "email": "ravi.agent@example.com", "mobile": "9000000011", "password": "agent123",
         "area": "Banjara Hills", "city": "Hyderabad", "location": {"lat": 17.4126, "lng": 78.4482}}


def form(**overrides) -> dict:
    data = {
        "fullName": "Usman Khan", "mobile": "9898989898", "email": "usman@example.com",
        "dob": date(date.today().year - 30, 5, 20).isoformat(), "aadhaar": "234567890120", "pan": "ABCPK1234D",
        "amount": 200000, "tenure": 24, "purpose": "Education", "income": 60000, "employment": "Self-employed",
        "address": "12 Road No. 3, Banjara Hills", "city": "Hyderabad", "pincode": "500034", "location": NEAR,
        "bank": {"holder": "Usman Khan", "account": "50100234567890", "ifsc": "HDFC0001234", "type": "Savings"},
        "consent": True,
    }
    return {**data, **overrides}


def files(*keys: str) -> dict:
    keys = keys or ("pan", "aadhaar", "bank", "address")
    return {k: (f"{k}.pdf", PDF, "application/pdf") for k in keys}


async def sign_up(client, **overrides) -> dict:
    res = await client.post("/auth/register", json={**CUSTOMER, **overrides})
    return {"Authorization": f"Bearer {res.json()['accessToken']}"}


async def submit(client, headers, data=None, upload=None):
    return await client.post("/applications", headers=headers,
                             data={"data": json.dumps(data or form())}, files=upload if upload is not None else files())


@pytest.mark.asyncio
async def test_options_come_from_the_server(client):
    headers = await sign_up(client)
    res = await client.get("/applications/options", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert "Education" in body["loanPurposes"] and 24 in body["tenuresMonths"]
    assert body["loanAmount"] == {"min": 10000, "max": 5000000}
    salary = next(d for d in body["documents"]["types"] if d["key"] == "salary")
    assert salary["onlyFor"] == "Salaried"


@pytest.mark.asyncio
async def test_customer_submits_application_with_documents(client, manager_headers):
    await client.post("/agents", json=AGENT, headers=manager_headers)
    headers = await sign_up(client)

    res = await submit(client, headers)

    assert res.status_code == 201, res.text
    body = res.json()
    app = body["application"]
    assert app["id"] == "LN-1001" and app["status"] == "unassigned"
    assert body["areaAgents"] == 1
    assert app["bank"]["bankName"] == "HDFC Bank"
    assert app["location"] == NEAR
    assert set(app["documents"]) == {"pan", "aadhaar", "bank", "address"}
    assert "fileId" not in app["documents"]["pan"]
    assert [h["action"] for h in app["history"]] == ["Application submitted", "Sent to manager & area agents"]

    doc = await client.get(f"/applications/{app['id']}/documents/pan", headers=headers)
    assert doc.status_code == 200 and doc.content == PDF
    assert doc.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_validation_errors_are_per_field(client):
    headers = await sign_up(client)
    res = await submit(client, headers, form(pan="ABCDE1234F", amount=5000, tenure=7, purpose="Holiday"))
    assert res.status_code == 422
    details = res.json()["error"]["details"]
    assert {"pan", "amount", "tenure", "purpose"} <= set(details)


@pytest.mark.asyncio
async def test_salaried_applicant_must_upload_salary_slips(client):
    headers = await sign_up(client)
    res = await submit(client, headers, form(employment="Salaried"))
    assert res.status_code == 422
    assert "doc_salary" in res.json()["error"]["details"]


@pytest.mark.asyncio
async def test_rejects_files_that_are_not_what_they_claim(client):
    headers = await sign_up(client)
    upload = {**files(), "pan": ("pan.pdf", b"MZ not really a pdf", "application/pdf")}
    res = await submit(client, headers, upload=upload)
    assert res.status_code == 422
    assert res.json()["error"]["details"]["doc_pan"] == "Upload a JPG, PNG, WEBP or PDF file."


@pytest.mark.asyncio
async def test_png_documents_are_accepted(client):
    headers = await sign_up(client)
    upload = {**files(), "aadhaar": ("aadhaar.png", PNG, "image/png")}
    assert (await submit(client, headers, upload=upload)).status_code == 201


@pytest.mark.asyncio
async def test_only_customers_can_submit(client, manager_headers):
    assert (await submit(client, manager_headers)).status_code == 403


@pytest.mark.asyncio
async def test_lists_are_scoped_by_role(client, manager_headers):
    await client.post("/agents", json=AGENT, headers=manager_headers)
    usman = await sign_up(client)
    other = await sign_up(client, email="asha@example.com", mobile="9797979797", name="Asha Rao")
    near_app = (await submit(client, usman)).json()["application"]["id"]
    far_app = (await submit(client, other, form(location=FAR))).json()["application"]["id"]

    mine = (await client.get("/applications", headers=usman)).json()
    assert [a["id"] for a in mine] == [near_app]

    everything = (await client.get("/applications", headers=manager_headers)).json()
    assert [a["id"] for a in everything] == [far_app, near_app]  # newest first

    login = await client.post("/auth/login", json={"identifier": AGENT["email"], "password": AGENT["password"]})
    agent = {"Authorization": f"Bearer {login.json()['accessToken']}"}
    in_area = (await client.get("/applications", headers=agent)).json()
    assert [a["id"] for a in in_area] == [near_app]

    # documents follow the same rules
    assert (await client.get(f"/applications/{far_app}/documents/pan", headers=usman)).status_code == 403
    assert (await client.get(f"/applications/{far_app}/documents/pan", headers=agent)).status_code == 403
    assert (await client.get(f"/applications/{far_app}/documents/pan", headers=manager_headers)).status_code == 200


@pytest.mark.asyncio
async def test_nearby_agents_hide_contact_details(client, manager_headers):
    await client.post("/agents", json=AGENT, headers=manager_headers)
    await client.post("/agents", json={**AGENT, "email": "far@example.com", "mobile": "9000000012",
                                       "location": FAR}, headers=manager_headers)
    headers = await sign_up(client)

    res = await client.get("/agents/nearby", params=NEAR, headers=headers)

    assert res.status_code == 200
    agents = res.json()
    assert len(agents) == 1
    assert agents[0]["name"] == "Ravi Kumar" and agents[0]["distanceKm"] < 2
    assert "email" not in agents[0] and "mobile" not in agents[0]


@pytest.mark.asyncio
async def test_new_customer_appears_in_managers_customer_list(client, manager_headers):
    await sign_up(client)

    res = await client.get("/customers", headers=manager_headers)

    assert res.status_code == 200
    assert [(c["name"], c["role"]) for c in res.json()] == [("Usman Khan", "customer")]
    customer = await sign_up(client, email="asha@example.com", mobile="9797979797")
    assert (await client.get("/customers", headers=customer)).status_code == 403


# Test PANs and their simulated scores: ABCPK1234D 805 (Excellent), ABAPG5678D 729 (Good),
# ABAPA1234D 651 (Fair), ABAPC1234D 526 (Poor - not eligible).
@pytest.mark.parametrize(("pan", "income", "tenure", "rate"), [
    ("ABCPK1234D", 60000, 24, 10.0),  # 0 points
    ("ABCPK1234D", 30000, 24, 11.4),  # income +1
    ("ABAPG5678D", 30000, 24, 14.0),  # score 700-749 +1, income +1
    ("ABAPA1234D", 30000, 48, 15.0),  # score 650-699 +2, income +1, tenure +1 -> capped at the last rate
])
@pytest.mark.asyncio
async def test_quote_and_saved_application_use_the_same_price(client, pan, income, tenure, rate):
    headers = await sign_up(client)
    quote = (await client.post("/eligibility/quote", headers=headers,
                               json={"pan": pan, "amount": 200000, "income": income, "tenure": tenure})).json()
    assert quote["ratePa"] == rate
    assert quote["totalPayable"] == quote["emi"] * tenure
    assert quote["totalInterest"] == quote["totalPayable"] - 200000

    app = (await submit(client, headers, form(pan=pan, income=income, tenure=tenure))).json()["application"]
    assert (app["creditScore"], app["interestRatePa"], app["emi"]) == (quote["creditScore"], rate, quote["emi"])


@pytest.mark.asyncio
async def test_quote_with_only_pan_returns_the_credit_score(client):
    headers = await sign_up(client)
    res = await client.post("/eligibility/quote", headers=headers, json={"pan": "ABCPK1234D"})
    assert res.status_code == 200
    assert res.json() == {"creditScore": 805, "creditBand": "Excellent", "eligible": True, "minCreditScore": 650}


@pytest.mark.asyncio
async def test_low_credit_score_is_not_eligible_and_cannot_submit(client):
    headers = await sign_up(client)
    quote = (await client.post("/eligibility/quote", headers=headers,
                               json={"pan": "ABAPC1234D", "amount": 200000, "income": 60000, "tenure": 24})).json()
    assert quote["eligible"] is False and quote["creditScore"] == 526 and "ratePa" not in quote

    res = await submit(client, headers, form(pan="ABAPC1234D"))
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "CREDIT_SCORE_TOO_LOW"
    assert "pan" in res.json()["error"]["details"]


@pytest.mark.asyncio
async def test_quote_rejects_bad_pan_and_non_customers(client, manager_headers):
    headers = await sign_up(client)
    assert (await client.post("/eligibility/quote", headers=headers, json={"pan": "ABCDE1234F"})).status_code == 422
    assert (await client.post("/eligibility/quote", headers=manager_headers,
                              json={"pan": "ABCPK1234D"})).status_code == 403
