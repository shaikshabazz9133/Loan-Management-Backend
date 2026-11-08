"""MongoDB queries for uploaded documents."""

from typing import Any

from bson import ObjectId
from app.db.mongo import get_database


def _id_values(user_id: str) -> list[Any]:
    values: list[Any] = [user_id]
    if ObjectId.is_valid(user_id):
        values.append(ObjectId(user_id))
    return values


class DocumentRepository:
    def __init__(self) -> None:
        self.documents = get_database()["documents"]

    async def insert(self, document: dict[str, Any]) -> ObjectId:
        result = await self.documents.insert_one(document)
        return result.inserted_id

    async def find_owned(
        self, document_id: ObjectId, customer_id: str
    ) -> dict[str, Any] | None:
        return await self.documents.find_one({
            "_id": document_id,
            "customer_id": {"$in": _id_values(customer_id)},
        })
