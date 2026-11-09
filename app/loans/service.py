"""Loan application rules: guest submit (with documents), status tracking, role-scoped listing, the
agent/manager workflow and document access.

Who sees what:
    applicant - no account; tracks one application with its id + mobile number (POST /applications/track)
    agent     - every open (unassigned) application, plus the ones they accepted
    manager   - every application
"""
import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import UploadFile

from app.common.enums import Role
from app.common.validators import bank_name_from_ifsc
from app.core.config import BUSINESS_RULES, DISBURSEMENT, DOCUMENTS
from app.core.exceptions import BadRequest, Conflict, Forbidden, NotFound, Unprocessable
from app.eligibility.emi import credit_score_for, emi_for, interest_rate_for
from app.loans import repository
from app.loans.models import history_entry
from app.loans.schemas import ActionRequest, ApplicationCreate, ApplicationOut, SubmitResponse, TrackOut, TrackRequest
from app.loans.state_machine import AGENT_OWNED_ACTIONS, HISTORY_ACTION, TRANSITIONS, UNASSIGNED
from app.users import repository as users_repository

# First bytes of each allowed file type, so a renamed .exe can't pass as a PDF.
_SIGNATURES = {
    "application/pdf": lambda b: b.startswith(b"%PDF"),
    "image/png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
    "image/webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP",
}


def _required_doc_types(employment: str) -> list[dict]:
    return [d for d in DOCUMENTS["types"] if not d.get("only_for") or d["only_for"] == employment]


async def _read_documents(files: dict[str, UploadFile], employment: str) -> dict[str, dict[str, Any]]:
    """Check every file (type, size, required set) and read it into memory. Errors are keyed doc_<type> like the form."""
    max_bytes = DOCUMENTS["max_size_mb"] * 1024 * 1024
    known = {d["key"]: d for d in DOCUMENTS["types"]}
    errors: dict[str, str] = {}
    read: dict[str, dict[str, Any]] = {}

    for doc in _required_doc_types(employment):
        if doc["key"] not in files:
            errors[f"doc_{doc['key']}"] = f"Upload your {doc['label'].lower()}."

    for key, upload in files.items():
        if key not in known:
            continue  # ignore unexpected parts
        data = await upload.read(max_bytes + 1)
        content_type = (upload.content_type or "").lower()
        if len(data) > max_bytes:
            errors[f"doc_{key}"] = f"File is larger than {DOCUMENTS['max_size_mb']} MB."
        elif not data:
            errors[f"doc_{key}"] = "The file is empty."
        elif content_type not in DOCUMENTS["allowed_mime_types"] or not _SIGNATURES[content_type](data):
            errors[f"doc_{key}"] = "Upload a JPG, PNG, WEBP or PDF file."
        else:
            read[key] = {"name": (upload.filename or key)[:200], "content_type": content_type, "data": data}

    if errors:
        raise Unprocessable("VALIDATION_ERROR", next(iter(errors.values())), errors)
    return read


# ---------- applicant (no login) ----------

async def submit(data: ApplicationCreate, files: dict[str, UploadFile]) -> SubmitResponse:
    credit_score = credit_score_for(data.pan)
    rate = interest_rate_for(credit_score, data.income, data.tenure)
    if rate is None:
        minimum = BUSINESS_RULES["min_credit_score"]
        message = f"Your credit score {credit_score} is below the minimum of {minimum}, so we can't offer a loan right now."
        raise Unprocessable("CREDIT_SCORE_TOO_LOW", message, {"pan": message})
    documents = await _read_documents(files, data.employment)
    now = datetime.now(UTC)
    number = await users_repository.next_sequence("application_no")
    application_id = f"LN-{1000 + number}"  # LN-1001, LN-1002, ...

    file_ids = await repository.insert_files([
        {"application_id": application_id, "doc_type": key, "name": d["name"], "content_type": d["content_type"],
         "size": len(d["data"]), "data": d["data"], "uploaded_at": now}
        for key, d in documents.items()
    ])

    application = {
        "_id": application_id,
        "customer_id": data.mobile,
        "agent_id": None,
        "agent_name": None,
        "status": UNASSIGNED,
        **data.model_dump(exclude={"bank", "consent", "dob"}),
        "dob": data.dob.isoformat(),
        "credit_score": credit_score,
        "interest_rate_pa": rate,
        "emi": emi_for(data.amount, data.tenure, rate),
        "bank": {**data.bank.model_dump(), "bank_name": bank_name_from_ifsc(data.bank.ifsc)},
        "documents": {
            key: {"file_id": file_id, "name": d["name"], "size": len(d["data"]), "type": d["content_type"],
                  "uploaded_at": now}
            for (key, d), file_id in zip(documents.items(), file_ids, strict=True)
        },
        "agent_decision": None,
        "manager_decision": None,
        "disbursement": None,
        "consent_at": now,
        "history": [
            history_entry(now, {"role": "customer", "name": data.full_name}, "Application submitted",
                          f"Loan request for ₹{data.amount:,}"),
            history_entry(now, None, "Sent to agents", "Visible to every active agent. The first one to accept it reviews it."),
        ],
        "created_at": now,
        "updated_at": now,
    }
    try:
        await repository.insert(application)
    except Exception:
        await repository.delete_files(file_ids)  # don't leave orphaned files behind
        raise
    return SubmitResponse(application=ApplicationOut.from_doc(application))


async def track(data: TrackRequest) -> TrackOut:
    application = await repository.find_by_id(data.application_id)
    # Same answer for a wrong id and a wrong mobile, so nobody can probe which ids exist.
    if application is None or application["mobile"] != data.mobile:
        raise NotFound("APPLICATION_NOT_FOUND", "No application found with this ID and mobile number.")
    return TrackOut.from_doc(application)


# ---------- staff ----------

def _agent_can_see(application: dict, agent: dict) -> bool:
    return application["status"] == UNASSIGNED or application.get("agent_id") == agent["_id"]


async def list_for(user: dict) -> list[ApplicationOut]:
    if user["role"] == Role.MANAGER:
        docs = await repository.find({})
    else:
        docs = await repository.find({"$or": [{"status": UNASSIGNED}, {"agent_id": user["_id"]}]})
    return [ApplicationOut.from_doc(d) for d in docs]


async def get_document(application_id: str, doc_type: str, user: dict) -> dict:
    """The stored file (name, content_type, data) if this staff member may see the application."""
    application = await repository.find_by_id(application_id)
    if application is None:
        raise NotFound("APPLICATION_NOT_FOUND", "Application not found.")
    if user["role"] == Role.AGENT and not _agent_can_see(application, user):
        raise Forbidden("FORBIDDEN", "Another agent is handling this application.")
    meta = application["documents"].get(doc_type)
    stored = await repository.find_file(meta["file_id"]) if meta else None
    if stored is None:
        raise NotFound("DOCUMENT_NOT_FOUND", "Document not found.")
    return stored


def _utr(ifsc: str, now: datetime) -> str:
    """Simulated bank transfer reference, e.g. HDFCN26110912345678."""
    return f"{ifsc[:4]}N{now:%y%m%d}{secrets.randbelow(10**8):08d}"


def _check_disburse_mode(mode: str | None, amount: int) -> str:
    if mode not in DISBURSEMENT["modes"]:
        raise BadRequest("INVALID_MODE", f"Choose a transfer mode: {', '.join(DISBURSEMENT['modes'])}.")
    if mode == "IMPS" and amount > DISBURSEMENT["imps_max_amount"]:
        raise BadRequest("INVALID_MODE", f"IMPS allows up to ₹{DISBURSEMENT['imps_max_amount']:,}. Use NEFT or RTGS.")
    if mode == "RTGS" and amount < DISBURSEMENT["rtgs_min_amount"]:
        raise BadRequest("INVALID_MODE", f"RTGS is for ₹{DISBURSEMENT['rtgs_min_amount']:,} and above. Use IMPS or NEFT.")
    return mode


async def act(application_id: str, data: ActionRequest, user: dict) -> ApplicationOut:
    """Accept / approve / reject / disburse, following app/loans/state_machine.py."""
    role = user["role"]
    rule = TRANSITIONS.get((data.action, role))
    if rule is None:
        raise Forbidden("FORBIDDEN", f"A {role} can't {data.action} an application.")
    allowed_from, new_status = rule

    application = await repository.find_by_id(application_id)
    if application is None:
        raise NotFound("APPLICATION_NOT_FOUND", "Application not found.")
    if role == Role.AGENT and data.action in AGENT_OWNED_ACTIONS and application.get("agent_id") != user["_id"]:
        raise Forbidden("NOT_YOUR_APPLICATION", "Only the agent who accepted this application can decide on it.")
    if data.action == "reject" and (not data.reason or len(data.reason) < 3):
        raise Unprocessable("VALIDATION_ERROR", "Give a reason for the rejection.", {"reason": "Give a reason for the rejection."})

    now = datetime.now(UTC)
    by = user["name"]
    changes: dict[str, Any] = {"status": new_status, "updated_at": now}
    note = data.note
    if data.action == "accept":
        changes |= {"agent_id": user["_id"], "agent_name": by}
        note = f"{by} accepted this application"
    elif data.action in ("approve", "reject"):
        decision = ("recommended" if data.action == "approve" else "rejected") if role == Role.AGENT \
            else ("approved" if data.action == "approve" else "rejected")
        key = "agent_decision" if role == Role.AGENT else "manager_decision"
        changes[key] = {"decision": decision, "note": data.note, "reason": data.reason, "at": now, "by": by}
        note = data.reason if data.action == "reject" else data.note
    else:  # disburse
        mode = _check_disburse_mode(data.mode, application["amount"])
        utr = _utr(application["bank"]["ifsc"], now)
        changes["disbursement"] = {"amount": application["amount"], "mode": mode, "utr": utr, "at": now, "by": by}
        bank = application["bank"]
        note = f"₹{application['amount']:,} sent to {bank['bank_name']} •••• {bank['account'][-4:]} via {mode} · UTR {utr}"

    match: dict[str, Any] = {"status": {"$in": list(allowed_from)}}
    if role == Role.AGENT and data.action in AGENT_OWNED_ACTIONS:
        match["agent_id"] = user["_id"]
    updated = await repository.transition(application_id, match, changes,
                                          history_entry(now, user, HISTORY_ACTION[(data.action, role)], note))
    if updated is None:  # status changed since we read it (e.g. another agent accepted first)
        if data.action == "accept":
            raise Conflict("ALREADY_TAKEN", "Another agent has already accepted this application.")
        done = {"approve": "approved", "reject": "rejected", "disburse": "disbursed"}[data.action]
        raise Conflict("INVALID_STATUS", f"This application can't be {done} right now (status: {application['status']}).")
    return ApplicationOut.from_doc(updated)
