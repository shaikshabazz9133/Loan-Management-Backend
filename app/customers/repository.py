"""MongoDB queries for a customer's own data."""

from typing import Any

from bson import ObjectId
from app.db.mongo import get_database


def _id_values(user_id: str) -> list[Any]:
    values: list[Any] = [user_id]
    if ObjectId.is_valid(user_id):
        values.append(ObjectId(user_id))
    return values


class CustomerRepository:
    def __init__(self) -> None:
        db = get_database()
        self.users = db["users"]
        self.applications = db["applications"]
        self.documents = db["documents"]

    async def get_customer(self, user_id: str) -> dict[str, Any] | None:
        return await self.users.find_one({
            "_id": {"$in": _id_values(user_id)},
            "role": {"$in": ["customer", "CUSTOMER"]},
        })

    async def count_applications(self, user_id: str) -> int:
        return await self.applications.count_documents({
            "customer_id": {"$in": _id_values(user_id)}
        })

    async def application_counts_by_status(
        self, user_id: str
    ) -> dict[str, int]:
        pipeline = [
            {"$match": {"customer_id": {"$in": _id_values(user_id)}}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        cursor = self.applications.aggregate(pipeline)
        return {
            str(row.get("_id", "")).lower(): row["count"]
            async for row in cursor
        }

    async def list_applications(
        self, user_id: str, *, skip: int, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        query = {"customer_id": {"$in": _id_values(user_id)}}
        total = await self.applications.count_documents(query)
        cursor = (
            self.applications.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [row async for row in cursor], total

    async def list_documents(self, user_id: str) -> list[dict[str, Any]]:
        cursor = (
            self.documents.find(
                {"customer_id": {"$in": _id_values(user_id)}},
                {"content": 0},
            )
            .sort("created_at", -1)
        )
        return [row async for row in cursor]
