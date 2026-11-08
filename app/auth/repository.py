"""MongoDB access for customer authentication."""

from typing import Any

from app.db.mongo import get_database


class AuthRepository:
    def __init__(self) -> None:
        self.users = get_database()["users"]

    async def find_by_email_or_phone(self, identifier: str) -> dict[str, Any] | None:
        return await self.users.find_one({
            "$or": [
                {"email": identifier.lower()},
                {"phone": identifier},
            ]
        })

    async def email_or_phone_exists(self, email: str, phone: str) -> bool:
        return await self.users.find_one({
            "$or": [{"email": email.lower()}, {"phone": phone}]
        }) is not None

    async def create_customer(self, customer: dict[str, Any]) -> str:
        result = await self.users.insert_one(customer)
        return str(result.inserted_id)
