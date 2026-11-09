"""Loan application rules: submit (with documents), role-scoped listing and document access.

Who sees what (GET /applications):
    customer - only their own applications
    manager  - every application
    agent    - open (unassigned) requests within their radius, plus any assigned to them
"""
from datetime import UTC, datetime
from typing import Any

from fastapi import UploadFile

from app.agents.service import nearby_agents
from app.common.enums import Role
from app.common.geo import distance_km
from app.common.validators import bank_name_from_ifsc
from app.eligibility.emi import credit_score_for, emi_for, interest_rate_for
from app.core.config import BUSINESS_RULES, DOCUMENTS
from app.core.exceptions import Forbidden, NotFound, Unprocessable
from app.loans import repository
from app.loans.models import history_entry
from app.loans.schemas import ApplicationCreate, ApplicationOut, SubmitResponse
from app.users import repository as users_repository
from app.users.models import geo_point

UNASSIGNED = "unassigned"

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


async def submit(data: ApplicationCreate, files: dict[str, UploadFile], customer: dict) -> SubmitResponse:
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

    location = data.location.model_dump()
    area_agents = len(await nearby_agents(location))
    radius = BUSINESS_RULES["assignment_radius_km"]
    shared_note = (
        f"Visible to the manager and {area_agents} agent{'s' if area_agents != 1 else ''} within {radius} km"
        if area_agents else "Visible to the manager. No active agent covers this location yet"
    )
    application = {
        "_id": application_id,
        "customer_id": customer["_id"],
        "agent_id": None,
        "status": UNASSIGNED,
        **data.model_dump(exclude={"location", "bank", "consent", "dob"}),
        "dob": data.dob.isoformat(),
        "credit_score": credit_score,
        "interest_rate_pa": rate,
        "emi": emi_for(data.amount, data.tenure, rate),
        "location": geo_point(location["lat"], location["lng"]),
        "bank": {**data.bank.model_dump(), "bank_name": bank_name_from_ifsc(data.bank.ifsc)},
        "documents": {
            key: {"file_id": file_id, "name": d["name"], "size": len(d["data"]), "type": d["content_type"],
                  "uploaded_at": now}
            for (key, d), file_id in zip(documents.items(), file_ids, strict=True)
        },
        "consent_at": now,
        "history": [
            history_entry(now, customer, "Application submitted", f"Loan request for ₹{data.amount:,}"),
            history_entry(now, None, "Sent to manager & area agents", shared_note),
        ],
        "created_at": now,
        "updated_at": now,
    }
    try:
        await repository.insert(application)
    except Exception:
        await repository.delete_files(file_ids)  # don't leave orphaned files behind
        raise
    return SubmitResponse(application=ApplicationOut.from_doc(application), area_agents=area_agents)


def _agent_can_see(application: dict, agent: dict) -> bool:
    if application.get("agent_id") == agent["_id"]:
        return True
    return (
        application["status"] == UNASSIGNED
        and bool(agent.get("location"))
        and distance_km(application["location"], agent["location"]) <= BUSINESS_RULES["assignment_radius_km"]
    )


async def list_for(user: dict) -> list[ApplicationOut]:
    role = user["role"]
    if role == Role.CUSTOMER:
        docs = await repository.find({"customer_id": user["_id"]})
    elif role == Role.MANAGER:
        docs = await repository.find({})
    else:
        candidates = await repository.find({"$or": [{"status": UNASSIGNED}, {"agent_id": user["_id"]}]})
        docs = [d for d in candidates if _agent_can_see(d, user)]
    return [ApplicationOut.from_doc(d) for d in docs]


async def get_document(application_id: str, doc_type: str, user: dict) -> dict:
    """The stored file (name, content_type, data) if this user may see the application."""
    application = await repository.find_by_id(application_id)
    if application is None:
        raise NotFound("APPLICATION_NOT_FOUND", "Application not found.")
    allowed = (
        user["role"] == Role.MANAGER
        or (user["role"] == Role.CUSTOMER and application["customer_id"] == user["_id"])
        or (user["role"] == Role.AGENT and _agent_can_see(application, user))
    )
    if not allowed:
        raise Forbidden("FORBIDDEN", "You do not have permission to view this document.")
    meta = application["documents"].get(doc_type)
    stored = await repository.find_file(meta["file_id"]) if meta else None
    if stored is None:
        raise NotFound("DOCUMENT_NOT_FOUND", "Document not found.")
    return stored
