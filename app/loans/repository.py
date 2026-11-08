"""MongoDB queries for loan applications."""

from typing import Any

from bson import ObjectId
from app.db.mongo import get_database


def _id_values(user_id: str) -> list[Any]:
    values: list[Any] = [user_id]
    if ObjectId.is_valid(user_id):
        values.append(ObjectId(user_id))
    return values


class LoanRepository:
    def __init__(self) -> None:
        self.applications = get_database()["applications"]

    async def insert(self, document: dict[str, Any]) -> ObjectId:
        result = await self.applications.insert_one(document)
        return result.inserted_id

    async def find_owned(
        self, loan_id: ObjectId, customer_id: str
    ) -> dict[str, Any] | None:
        return await self.applications.find_one({
            "_id": loan_id,
            "customer_id": {"$in": _id_values(customer_id)},
        })

    async def list_owned(
        self, customer_id: str, *, skip: int, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        query = {"customer_id": {"$in": _id_values(customer_id)}}
        total = await self.applications.count_documents(query)
        cursor = (
            self.applications.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [row async for row in cursor], total

    async def cancel_if_open(
        self, loan_id: ObjectId, customer_id: str, now
    ) -> bool:
        result = await self.applications.update_one(
            {
                "_id": loan_id,
                "customer_id": {"$in": _id_values(customer_id)},
                "status": {"$in": ["submitted", "assigned"]},
                "assignment.accepted_at": {"$exists": False},
            },
            {
                "$set": {"status": "cancelled", "updated_at": now},
                "$push": {
                    "timeline": {
                        "status": "cancelled",
                        "at": now,
                        "note": "Cancelled by customer",
                    }
                },
            },
        )
        return result.modified_count == 1
