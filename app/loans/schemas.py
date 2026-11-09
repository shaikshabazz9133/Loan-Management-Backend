"""Request/response bodies for loan applications (camelCase JSON, see app/common/responses.py).

ApplicationCreate is the "data" part of the multipart POST /applications; the documents travel as files
in the same request. Field names match the frontend form, so validation errors land under the right input.
Customers have no account: an application is identified by its id (LN-1001) + the applicant's mobile number.
"""
from typing import Literal

from datetime import date, datetime

from pydantic import EmailStr, Field, field_validator

from app.common.responses import CamelModel
from app.common.validators import (
    normalize_aadhaar,
    normalize_account_number,
    normalize_email,
    normalize_ifsc,
    normalize_mobile,
    normalize_pan,
)
from app.core.config import BUSINESS_RULES, DOCUMENTS, get_settings


def _age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _one_of(value: str, allowed: list[str], what: str) -> str:
    if value not in allowed:
        raise ValueError(f"Select a valid {what}.")
    return value


def _strip(v):
    return v.strip() if isinstance(v, str) else v


# ---------- request ----------
class BankAccountIn(CamelModel):
    holder: str = Field(min_length=3, max_length=100)
    account: str
    ifsc: str
    type: str = "Savings"

    @field_validator("holder", mode="before")
    @classmethod
    def _strip_holder(cls, v):
        return _strip(v)

    @field_validator("account")
    @classmethod
    def _account(cls, v: str) -> str:
        return normalize_account_number(v)

    @field_validator("ifsc")
    @classmethod
    def _ifsc(cls, v: str) -> str:
        return normalize_ifsc(v)

    @field_validator("type")
    @classmethod
    def _type(cls, v: str) -> str:
        return _one_of(v, BUSINESS_RULES["bank_account_types"], "account type")


class ApplicationCreate(CamelModel):
    # personal & KYC
    full_name: str = Field(min_length=3, max_length=100)
    mobile: str
    email: EmailStr
    dob: date
    aadhaar: str
    pan: str
    # loan
    amount: int
    tenure: int
    purpose: str
    income: int
    employment: str
    # address
    address: str = Field(min_length=5, max_length=300)
    city: str = Field(min_length=2, max_length=100)
    pincode: str = Field(pattern=r"^\d{6}$")
    # disbursement account
    bank: BankAccountIn
    consent: bool

    @field_validator("full_name", "address", "city", mode="before")
    @classmethod
    def _strip_text(cls, v):
        return _strip(v)

    @field_validator("mobile")
    @classmethod
    def _mobile(cls, v: str) -> str:
        return normalize_mobile(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalize_email(v)

    @field_validator("dob")
    @classmethod
    def _dob(cls, v: date) -> date:
        limits = BUSINESS_RULES["applicant_age"]
        age = _age_on(v, date.today())
        if not limits["min"] <= age <= limits["max"]:
            raise ValueError(f"Applicants must be between {limits['min']} and {limits['max']} years old (you are {age}).")
        return v

    @field_validator("aadhaar")
    @classmethod
    def _aadhaar(cls, v: str) -> str:
        return normalize_aadhaar(v, demo_mode=get_settings().aadhaar_demo_mode)

    @field_validator("pan")
    @classmethod
    def _pan(cls, v: str) -> str:
        return normalize_pan(v)

    @field_validator("amount")
    @classmethod
    def _amount(cls, v: int) -> int:
        limits = BUSINESS_RULES["loan_amount"]
        if not limits["min"] <= v <= limits["max"]:
            raise ValueError(f"Loan amount must be between ₹{limits['min']:,} and ₹{limits['max']:,}.")
        return v

    @field_validator("tenure")
    @classmethod
    def _tenure(cls, v: int) -> int:
        if v not in BUSINESS_RULES["tenures_months"]:
            raise ValueError("Choose a valid loan tenure.")
        return v

    @field_validator("purpose")
    @classmethod
    def _purpose(cls, v: str) -> str:
        return _one_of(v, BUSINESS_RULES["loan_purposes"], "loan purpose")

    @field_validator("employment")
    @classmethod
    def _employment(cls, v: str) -> str:
        return _one_of(v, BUSINESS_RULES["employment_types"], "employment type")

    @field_validator("income")
    @classmethod
    def _income(cls, v: int) -> int:
        minimum = BUSINESS_RULES["min_monthly_income"]
        if v < minimum:
            raise ValueError(f"Enter your monthly income (min ₹{minimum:,}).")
        return v

    @field_validator("consent")
    @classmethod
    def _consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Please accept the credit check consent to continue.")
        return v


# ---------- form options ----------
class DocumentType(CamelModel):
    key: str
    label: str
    hint: str
    only_for: str | None = None


class AmountRange(CamelModel):
    min: int
    max: int


class DocumentRules(CamelModel):
    max_size_mb: int
    allowed_mime_types: list[str]
    types: list[DocumentType]


class ApplicationOptions(CamelModel):
    """Everything the apply form needs: dropdown values, limits and document rules (no hardcoding in the UI)."""

    loan_purposes: list[str]
    employment_types: list[str]
    bank_account_types: list[str]
    tenures_months: list[int]
    loan_amount: AmountRange
    loan_amount_presets: list[int]
    min_monthly_income: int
    applicant_age: AmountRange
    max_foir: float
    min_credit_score: int
    aadhaar_demo_mode: bool
    documents: DocumentRules

    @classmethod
    def current(cls) -> "ApplicationOptions":
        rules = BUSINESS_RULES
        return cls(
            loan_purposes=rules["loan_purposes"],
            employment_types=rules["employment_types"],
            bank_account_types=rules["bank_account_types"],
            tenures_months=rules["tenures_months"],
            loan_amount=rules["loan_amount"],
            loan_amount_presets=rules["loan_amount_presets"],
            min_monthly_income=rules["min_monthly_income"],
            applicant_age=rules["applicant_age"],
            max_foir=rules["max_foir"],
            min_credit_score=rules["min_credit_score"],
            aadhaar_demo_mode=get_settings().aadhaar_demo_mode,
            documents=DocumentRules(
                max_size_mb=DOCUMENTS["max_size_mb"],
                allowed_mime_types=DOCUMENTS["allowed_mime_types"],
                types=DOCUMENTS["types"],
            ),
        )


# ---------- response ----------
class BankAccountOut(CamelModel):
    holder: str
    account: str
    ifsc: str
    bank_name: str
    type: str


class DocumentOut(CamelModel):
    name: str
    size: int
    type: str
    uploaded_at: datetime


class HistoryEntry(CamelModel):
    id: str
    at: datetime
    actor_role: str
    actor_name: str
    action: str
    note: str | None = None


class Decision(CamelModel):
    decision: str  # agent: "recommended" / "rejected"; manager: "approved" / "rejected"
    note: str | None = None
    reason: str | None = None  # required when rejected; shown to the customer
    at: datetime
    by: str


class Disbursement(CamelModel):
    amount: int
    mode: str  # IMPS / NEFT / RTGS
    utr: str  # bank transfer reference
    at: datetime
    by: str


class ApplicationOut(CamelModel):
    """Full application, for agents and managers."""

    id: str
    customer_id: str  # the applicant's mobile number (customers have no account)
    agent_id: str | None = None
    agent_name: str | None = None
    status: str
    full_name: str
    mobile: str
    email: str
    dob: str
    aadhaar: str
    pan: str
    amount: int
    tenure: int
    purpose: str
    income: int
    employment: str
    credit_score: int | None = None  # simulated bureau score at submission time
    interest_rate_pa: float | None = None  # priced from credit score, income and tenure at submission time
    emi: int | None = None
    address: str
    city: str
    pincode: str
    bank: BankAccountOut
    documents: dict[str, DocumentOut]
    agent_decision: Decision | None = None
    manager_decision: Decision | None = None
    disbursement: Disbursement | None = None
    history: list[HistoryEntry]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_doc(cls, doc: dict) -> "ApplicationOut":
        skip = {"_id", "customer_id", "agent_id", "documents"}
        return cls(
            **{k: v for k, v in doc.items() if k not in skip},
            id=doc["_id"],
            customer_id=doc["mobile"],
            agent_id=str(doc["agent_id"]) if doc.get("agent_id") else None,
            documents={key: {k: v for k, v in meta.items() if k != "file_id"} for key, meta in doc["documents"].items()},
        )


class SubmitResponse(CamelModel):
    application: ApplicationOut


# ---------- public status tracking (no login) ----------
class TrackRequest(CamelModel):
    application_id: str = Field(min_length=3, max_length=20)
    mobile: str

    @field_validator("application_id")
    @classmethod
    def _id(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("mobile")
    @classmethod
    def _mobile(cls, v: str) -> str:
        return normalize_mobile(v)


class StatusStep(CamelModel):
    action: str
    at: datetime


class CustomerDecision(CamelModel):
    decision: str
    reason: str | None = None  # only rejection reasons are shown to the customer
    at: datetime


class TrackOut(CamelModel):
    """What the applicant sees on the status page: no internal notes, no full ID or account numbers."""

    id: str
    status: str
    full_name: str
    amount: int
    tenure: int
    interest_rate_pa: float | None = None
    emi: int | None = None
    bank_label: str  # e.g. "HDFC Bank •••• 7890"
    agent_name: str | None = None
    agent_decision: CustomerDecision | None = None
    manager_decision: CustomerDecision | None = None
    disbursement: Disbursement | None = None
    steps: list[StatusStep]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_doc(cls, doc: dict) -> "TrackOut":
        def public(decision: dict | None) -> dict | None:
            if not decision:
                return None
            return {"decision": decision["decision"], "at": decision["at"],
                    "reason": decision.get("reason") if decision["decision"] == "rejected" else None}

        bank = doc["bank"]
        return cls(
            id=doc["_id"], status=doc["status"], full_name=doc["full_name"], amount=doc["amount"],
            tenure=doc["tenure"], interest_rate_pa=doc.get("interest_rate_pa"), emi=doc.get("emi"),
            bank_label=f"{bank['bank_name']} •••• {bank['account'][-4:]}", agent_name=doc.get("agent_name"),
            agent_decision=public(doc.get("agent_decision")), manager_decision=public(doc.get("manager_decision")),
            disbursement=doc.get("disbursement"),
            steps=[{"action": h["action"], "at": h["at"]} for h in doc["history"]],
            created_at=doc["created_at"], updated_at=doc["updated_at"],
        )


# ---------- agent / manager actions ----------
class ActionRequest(CamelModel):
    """One endpoint for every step: accept (agent), approve / reject (agent or manager), disburse (manager)."""

    action: Literal["accept", "approve", "reject", "disburse"]
    note: str | None = Field(default=None, max_length=500)
    reason: str | None = Field(default=None, max_length=500)  # required for reject
    mode: str | None = None  # required for disburse: IMPS / NEFT / RTGS

    @field_validator("note", "reason", mode="before")
    @classmethod
    def _strip_text(cls, v):
        v = _strip(v)
        return v or None
