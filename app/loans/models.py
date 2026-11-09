"""What is stored in MongoDB for a loan application.

"applications" collection (one document per application):
    _id            "LN-1001" (readable id shown to customers)
    customer_id    the applicant's mobile number (customers have no account)
    agent_id       ObjectId of the agent who accepted it, or None;  agent_name  their name
    status         see app/loans/state_machine.py (unassigned -> assigned -> ... -> disbursed)
    full_name, mobile, email, dob ("YYYY-MM-DD"), aadhaar, pan
    amount, tenure (months), purpose, income (monthly), employment
    credit_score, interest_rate_pa, emi
    address, city, pincode
    bank           {holder, account, ifsc, bank_name, type}
    documents      {"pan": {file_id, name, size, type, uploaded_at}, ...}
    agent_decision / manager_decision   {decision, note, reason, at, by}
    disbursement   {amount, mode, utr, at, by}
    history        [{id, at, actor_role, actor_name, action, note}]
    created_at, updated_at

"application_files" collection (the uploaded bytes, one document per file, max 5 MB each):
    _id, application_id, doc_type, name, content_type, size, data (binary), uploaded_at
"""
from datetime import datetime
from typing import Any
from uuid import uuid4


def history_entry(at: datetime, actor: dict | None, action: str, note: str | None = None) -> dict[str, Any]:
    return {
        "id": f"h-{uuid4().hex[:10]}",
        "at": at,
        "actor_role": actor["role"] if actor else "system",
        "actor_name": actor["name"] if actor else "System",
        "action": action,
        "note": note,
    }
