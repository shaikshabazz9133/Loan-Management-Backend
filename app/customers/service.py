"""Customer self-service business logic."""

from typing import Any

from fastapi import HTTPException

from app.customers.repository import CustomerRepository


IN_PROGRESS = {
    "submitted", "assigned", "agent_review", "manager_review",
    "pending", "under_review",
}


def _customer_id(current_user: dict) -> str:
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid customer token")
    return str(user_id)


def _name(customer: dict[str, Any]) -> str:
    if customer.get("name"):
        return customer["name"]
    return " ".join(
        part for part in (customer.get("first_name"), customer.get("last_name"))
        if part
    )


class CustomerService:
    def __init__(self) -> None:
        self.repository = CustomerRepository()

    async def dashboard(self, current_user: dict) -> dict[str, Any]:
        user_id = _customer_id(current_user)
        customer = await self.repository.get_customer(user_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer profile not found")

        counts = await self.repository.application_counts_by_status(user_id)
        return {
            "customer_id": user_id,
            "name": _name(customer),
            "total_applications": sum(counts.values()),
            "in_progress": sum(
                value for status, value in counts.items() if status in IN_PROGRESS
            ),
            "approved": counts.get("approved", 0),
            "rejected": counts.get("rejected", 0),
        }

    async def my_applications(
        self, current_user: dict, *, page: int, page_size: int
    ) -> dict[str, Any]:
        user_id = _customer_id(current_user)
        rows, total = await self.repository.list_applications(
            user_id,
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
                "employment": row.get("employment"),
                "city": str(row.get("city", "")),
                "status": str(row.get("status", "submitted")),
                "agent_id": str(row["agent_id"]) if row.get("agent_id") else None,
                "agent_name": row.get("agent_name"),
                "created_at": row.get("created_at"),
            })
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def my_documents(self, current_user: dict) -> list[dict[str, Any]]:
        user_id = _customer_id(current_user)
        rows = await self.repository.list_documents(user_id)
        return [
            {
                "id": str(row["_id"]),
                "loan_id": row.get("loan_id"),
                "document_type": row.get("document_type", ""),
                "filename": row.get("filename", ""),
                "content_type": row.get("content_type", "application/octet-stream"),
                "size_bytes": row.get("size_bytes", 0),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
