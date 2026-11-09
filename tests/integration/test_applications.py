"""Guest applies (no login) -> tracks status with id + mobile; any agent accepts (first wins) -> agent decides ->
manager decides -> manager disburses. Plus the customer list built from applications."""
import json
from datetime import date

import pytest

PDF = b"%PDF-1.4 test document"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
MOBILE = "9898989898"

AGENT = {"name": "Ravi Kumar", "email": "ravi.agent@example.com", "mobile": "9000000011", "password": "agent123",
         "area": "Banjara Hills", "city": "Hyderabad"}
AGENT_2 = {**AGENT, "name": "Priya Sharma", "email": "priya@example.com", "mobile": "9000000012"}


def form(**overrides) -> dict:
    data = {
        "fullName": "Usman Khan", "mobile": MOBILE, "email": "usman@example.com",
        "dob": date(date.today().year - 30, 5, 20).isoformat(), "aadhaar": "234567890120", "pan": "ABCPK1234D",
        "amount": 200000, "tenure": 24, "purpose": "Education", "income": 60000, "employment": "Self-employed",
        "address": "12 Road No. 3, Banjara Hills", "city": "Hyderabad", "pincode": "500034",
        "bank": {"holder": "Usman Khan", "account": "50100234567890", "ifsc": "HDFC0001234", "type": "Savings"},
        "consent": True,
    }
    return {**data, **overrides}


def files(*keys: str) -> dict:
    keys = keys or ("pan", "aadhaar", "bank", "address")
    return {k: (f"{k}.pdf", PDF, "application/pdf") for k in keys}


async def submit(client, data=None, upload=None):
    """No Authorization header: applicants don't have accounts."""
    return await client.post("/applications", data={"data": json.dumps(data or form())},
                             files=upload if upload is not None else files())


async def new_application(client, **overrides) -> str:
    res = await submit(client, form(**overrides))
    assert res.status_code == 201, res.text
    return res.json()["application"]["id"]


async def agent_login(client, manager_headers, agent=AGENT) -> dict:
    await client.post("/agents", json=agent, headers=manager_headers)
    login = await client.post("/auth/login", json={"identifier": agent["email"], "password": agent["password"]})
    return {"Authorization": f"Bearer {login.json()['accessToken']}"}


async def act(client, headers, app_id, action, **body):
    return await client.post(f"/applications/{app_id}/actions", headers=headers, json={"action": action, **body})


async def track(client, app_id, mobile=MOBILE):
    return await client.post("/applications/track", json={"applicationId": app_id, "mobile": mobile})


# ---------- applicant (public) ----------

@pytest.mark.asyncio
async def test_options_and_quote_are_public(client):
    options = await client.get("/applications/options")
    assert options.status_code == 200
    assert "Education" in options.json()["loanPurposes"] and "assignmentRadiusKm" not in options.json()

    quote = await client.post("/eligibility/quote", json={"pan": "ABCPK1234D", "amount": 200000, "income": 60000,
                                                          "tenure": 24})
    assert quote.status_code == 200
    assert (quote.json()["creditScore"], quote.json()["ratePa"], quote.json()["emi"]) == (805, 10.0, 9229)


@pytest.mark.asyncio
async def test_guest_submits_application_without_login(client):
    res = await submit(client)

    assert res.status_code == 201, res.text
    app = res.json()["application"]
    assert app["id"] == "LN-1001" and app["status"] == "unassigned"
    assert app["customerId"] == MOBILE
    assert (app["creditScore"], app["interestRatePa"], app["emi"]) == (805, 10.0, 9229)
    assert "location" not in app
    assert set(app["documents"]) == {"pan", "aadhaar", "bank", "address"}
    assert [h["action"] for h in app["history"]] == ["Application submitted", "Sent to agents"]


@pytest.mark.asyncio
async def test_validation_errors_are_per_field(client):
    res = await submit(client, form(pan="ABCDE1234F", amount=5000, tenure=7, purpose="Holiday"))
    assert res.status_code == 422
    assert {"pan", "amount", "tenure", "purpose"} <= set(res.json()["error"]["details"])


@pytest.mark.asyncio
async def test_document_rules(client):
    salaried = await submit(client, form(employment="Salaried"))
    assert "doc_salary" in salaried.json()["error"]["details"]

    fake = await submit(client, upload={**files(), "pan": ("pan.pdf", b"MZ not a pdf", "application/pdf")})
    assert fake.json()["error"]["details"]["doc_pan"] == "Upload a JPG, PNG, WEBP or PDF file."

    png = await submit(client, upload={**files(), "aadhaar": ("aadhaar.png", PNG, "image/png")})
    assert png.status_code == 201


@pytest.mark.asyncio
async def test_low_credit_score_cannot_submit(client):
    res = await submit(client, form(pan="ABAPC1234D"))  # simulated score 526
    assert res.status_code == 422 and res.json()["error"]["code"] == "CREDIT_SCORE_TOO_LOW"


@pytest.mark.asyncio
async def test_track_needs_matching_id_and_mobile_and_hides_sensitive_data(client):
    app_id = await new_application(client)

    res = await track(client, app_id.lower())  # id is case-insensitive
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "unassigned" and body["bankLabel"] == "HDFC Bank •••• 7890"
    assert [s["action"] for s in body["steps"]] == ["Application submitted", "Sent to agents"]
    for secret in ("aadhaar", "pan", "bank", "documents", "mobile", "email"):
        assert secret not in body

    wrong_mobile = await track(client, app_id, "9123456789")
    missing = await track(client, "LN-9999")
    assert wrong_mobile.status_code == missing.status_code == 404
    assert wrong_mobile.json() == missing.json()  # can't tell which ids exist


# ---------- staff workflow ----------

@pytest.mark.asyncio
async def test_staff_endpoints_need_sign_in(client):
    app_id = await new_application(client)
    assert (await client.get("/applications")).status_code == 401
    assert (await client.get(f"/applications/{app_id}/documents/pan")).status_code == 401
    assert (await client.post(f"/applications/{app_id}/actions", json={"action": "accept"})).status_code == 401


@pytest.mark.asyncio
async def test_full_flow_from_apply_to_disbursed(client, manager_headers):
    ravi = await agent_login(client, manager_headers)
    app_id = await new_application(client)

    # every agent sees the open application
    assert [a["id"] for a in (await client.get("/applications", headers=ravi)).json()] == [app_id]

    accepted = await act(client, ravi, app_id, "accept")
    assert accepted.status_code == 200
    assert (accepted.json()["status"], accepted.json()["agentName"]) == ("assigned", "Ravi Kumar")
    assert (await track(client, app_id)).json()["agentName"] == "Ravi Kumar"

    recommended = await act(client, ravi, app_id, "approve", note="Documents verified")
    assert recommended.json()["status"] == "agent_approved"
    assert recommended.json()["agentDecision"]["decision"] == "recommended"

    approved = await act(client, manager_headers, app_id, "approve")
    assert approved.json()["status"] == "approved"

    paid = await act(client, manager_headers, app_id, "disburse", mode="NEFT")
    assert paid.status_code == 200
    disbursement = paid.json()["disbursement"]
    assert paid.json()["status"] == "disbursed" and disbursement["amount"] == 200000
    assert disbursement["utr"].startswith("HDFCN")

    status = (await track(client, app_id)).json()
    assert status["status"] == "disbursed" and status["disbursement"]["utr"] == disbursement["utr"]
    assert [s["action"] for s in status["steps"]][-4:] == [
        "Accepted by agent", "Recommended for approval", "Loan approved", "Amount disbursed"]


@pytest.mark.asyncio
async def test_first_agent_to_accept_wins(client, manager_headers):
    ravi = await agent_login(client, manager_headers)
    priya = await agent_login(client, manager_headers, AGENT_2)
    app_id = await new_application(client)

    assert (await act(client, ravi, app_id, "accept")).status_code == 200
    late = await act(client, priya, app_id, "accept")
    assert late.status_code == 409 and late.json()["error"]["code"] == "ALREADY_TAKEN"

    assert (await client.get("/applications", headers=priya)).json() == []  # no longer open
    assert (await client.get(f"/applications/{app_id}/documents/pan", headers=priya)).status_code == 403
    assert (await client.get(f"/applications/{app_id}/documents/pan", headers=ravi)).content == PDF
    nope = await act(client, priya, app_id, "approve")
    assert nope.status_code == 403 and nope.json()["error"]["code"] == "NOT_YOUR_APPLICATION"


@pytest.mark.asyncio
async def test_steps_must_happen_in_order(client, manager_headers):
    ravi = await agent_login(client, manager_headers)
    app_id = await new_application(client)

    assert (await act(client, ravi, app_id, "approve")).status_code == 403  # not accepted yet
    assert (await act(client, manager_headers, app_id, "approve")).status_code == 409  # agent hasn't decided
    assert (await act(client, manager_headers, app_id, "accept")).status_code == 403  # managers don't accept
    assert (await act(client, ravi, app_id, "disburse", mode="NEFT")).status_code == 403  # agents don't pay


@pytest.mark.asyncio
async def test_rejection_needs_a_reason_and_customer_sees_it(client, manager_headers):
    ravi = await agent_login(client, manager_headers)
    app_id = await new_application(client)
    await act(client, ravi, app_id, "accept")

    assert (await act(client, ravi, app_id, "reject")).status_code == 422
    rejected = await act(client, ravi, app_id, "reject", reason="Income could not be verified", note="internal")
    assert rejected.json()["status"] == "agent_rejected"

    status = (await track(client, app_id)).json()
    assert status["agentDecision"] == {"decision": "rejected", "reason": "Income could not be verified",
                                       "at": status["agentDecision"]["at"]}


@pytest.mark.asyncio
async def test_manager_can_reject_before_any_agent_and_disburse_mode_is_checked(client, manager_headers):
    app_id = await new_application(client)
    rejected = await act(client, manager_headers, app_id, "reject", reason="Duplicate application")
    assert rejected.json()["status"] == "rejected"

    ravi = await agent_login(client, manager_headers)
    big = await new_application(client, amount=600000)
    await act(client, ravi, big, "accept")
    await act(client, ravi, big, "approve")
    await act(client, manager_headers, big, "approve")
    imps = await act(client, manager_headers, big, "disburse", mode="IMPS")  # IMPS max ₹5,00,000
    assert imps.status_code == 400 and imps.json()["error"]["code"] == "INVALID_MODE"
    assert (await act(client, manager_headers, big, "disburse", mode="RTGS")).status_code == 200


@pytest.mark.asyncio
async def test_deactivated_agent_returns_work_and_cannot_be_deleted_with_history(client, manager_headers):
    ravi = await agent_login(client, manager_headers)
    agent_id = (await client.get("/agents", headers=manager_headers)).json()[0]["id"]
    app_id = await new_application(client)
    await act(client, ravi, app_id, "accept")

    deleted = await client.delete(f"/agents/{agent_id}", headers=manager_headers)
    assert deleted.status_code == 409 and deleted.json()["error"]["code"] == "AGENT_HAS_APPLICATIONS"

    await client.patch(f"/agents/{agent_id}", json={"active": False}, headers=manager_headers)
    app = (await client.get("/applications", headers=manager_headers)).json()[0]
    assert app["status"] == "unassigned" and "agentId" not in app
    assert app["history"][-1]["action"] == "Returned to open applications"


# ---------- customers ----------

@pytest.mark.asyncio
async def test_manager_sees_applicants_as_customers(client, manager_headers):
    await new_application(client)
    await new_application(client, fullName="Usman K")  # same mobile -> same customer
    await new_application(client, mobile="9797979797", fullName="Asha Rao", email="asha@example.com")

    res = await client.get("/customers", headers=manager_headers)
    assert res.status_code == 200
    assert [(c["name"], c["mobile"], c["applications"]) for c in res.json()] == [
        ("Asha Rao", "9797979797", 1), ("Usman K", MOBILE, 2)]
    assert (await client.get("/customers")).status_code == 401
