"""Loan application business logic for customer self-service."""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException

from app.customers.repository import CustomerRepository
from app.loans.repository import LoanRepository
from app.loans.schemas import LoanApplicationCreate


def _customer_id(current_user: dict) -> str:
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid customer token")
    return str(user_id)


def _public(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result["id"] = str(result.pop("_id"))
    return result


def _loan_object_id(loan_id: str) -> ObjectId:
    if not ObjectId.is_valid(loan_id):
        raise HTTPException(status_code=404, detail="Loan application not found")
    return ObjectId(loan_id)


class LoanService:
    def __init__(self) -> None:
        self.repository = LoanRepository()
        self.customers = CustomerRepository()

    async def create_application(
        self,
        current_user: dict,
        payload: LoanApplicationCreate,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        customer_id = _customer_id(current_user)
        customer = await self.customers.get_customer(customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer profile not found")

        now = datetime.now(timezone.utc)
        application = payload.model_dump()
        application.update({
            "customer_id": customer_id,
            "status": "submitted",
            "assignment": {"status": "unassigned", "agent_id": None},
            "agent_id": None,
            "agent_name": None,
            "idempotency_key": idempotency_key,
            "created_at": now,
            "updated_at": now,
            "timeline": [{
                "status": "submitted",
                "at": now,
                "note": "Application submitted by customer",
            }],
        })

        # Use account details for contact values when available; keep the
        # submitted values as a snapshot if the account has no such field.
        application["name"] = customer.get("name") or application["name"]
        application["email"] = customer.get("email") or application["email"]
        application["phone"] = customer.get("phone") or application["phone"]

        loan_id = await self.repository.insert(application)
        application["_id"] = loan_id
        return _public(application)

    async def get_application(
        self, current_user: dict, loan_id: str
    ) -> dict[str, Any]:
        record = await self.repository.find_owned(
            _loan_object_id(loan_id), _customer_id(current_user)
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Loan application not found")
        return _public(record)

    async def list_my_applications(
        self, current_user: dict, *, page: int, page_size: int
    ) -> dict[str, Any]:
        rows, total = await self.repository.list_owned(
            _customer_id(current_user),
            skip=(page - 1) * page_size,
            limit=page_size,
        )
        items = []
        for row in rows:
            items.append({
                "id": str(row["_id"]),
                "amount": float(row.get("amount", 0)),
                "purpose": str(row.get("purpose", "")),
                "income": float(row.get("income", 0)),
                "employment": str(row.get("employment", "")),
                "city": str(row.get("city", "")),
                "status": str(row.get("status", "submitted")),
                "agent_id": str(row["agent_id"]) if row.get("agent_id") else None,
                "agent_name": row.get("agent_name"),
                "created_at": row["created_at"],
            })
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def timeline(self, current_user: dict, loan_id: str) -> dict[str, Any]:
        record = await self.repository.find_owned(
            _loan_object_id(loan_id), _customer_id(current_user)
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Loan application not found")
        return {"loan_id": loan_id, "events": record.get("timeline", [])}

    async def assignment(self, current_user: dict, loan_id: str) -> dict[str, Any]:
        record = await self.repository.find_owned(
            _loan_object_id(loan_id), _customer_id(current_user)
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Loan application not found")
        assignment = record.get("assignment") or {
            "status": "unassigned",
            "agent_id": record.get("agent_id"),
        }
        return {"loan_id": loan_id, **assignment}

    async def cancel(self, current_user: dict, loan_id: str) -> dict[str, Any]:
        oid = _loan_object_id(loan_id)
        customer_id = _customer_id(current_user)
        record = await self.repository.find_owned(oid, customer_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Loan application not found")

        now = datetime.now(timezone.utc)
        changed = await self.repository.cancel_if_open(oid, customer_id, now)
        if not changed:
            raise HTTPException(
                status_code=409,
                detail="This application can no longer be cancelled",
            )
        return {"loan_id": loan_id, "status": "cancelled"}
