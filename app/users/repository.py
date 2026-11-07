"""All MongoDB queries for the "users" collection. No business rules here - only reading and writing."""
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.common.validators import looks_like_email, normalize_email, normalize_mobile
from app.core.exceptions import Conflict
from app.db.mongo import get_database


def _users():
    return get_database().users


async def find_by_id(user_id: str) -> dict | None:
    if not ObjectId.is_valid(user_id):
        return None
    return await _users().find_one({"_id": ObjectId(user_id)})


async def find_by_email(email: str) -> dict | None:
    return await _users().find_one({"email": normalize_email(email)})


async def find_by_mobile(mobile: str) -> dict | None:
    return await _users().find_one({"mobile": mobile})


async def find_by_identifier(identifier: str) -> dict | None:
    """Login accepts an email OR a mobile number in the same box."""
    identifier = identifier.strip()
    if looks_like_email(identifier):
        return await find_by_email(identifier)
    try:
        return await find_by_mobile(normalize_mobile(identifier))
    except ValueError:
        return None


async def insert(user: dict[str, Any]) -> dict[str, Any]:
    try:
        result = await _users().insert_one(user)
    except DuplicateKeyError:  # unique index caught a duplicate that slipped past the service check
        raise Conflict("ACCOUNT_EXISTS", "An account with this email or mobile number already exists.") from None
    return {**user, "_id": result.inserted_id}


async def update(user_id: ObjectId, changes: dict[str, Any]) -> dict | None:
    """Apply changes and return the updated document."""
    try:
        return await _users().find_one_and_update(
            {"_id": user_id}, {"$set": changes}, return_document=ReturnDocument.AFTER
        )
    except DuplicateKeyError:
        raise Conflict("ACCOUNT_EXISTS", "An account with this email or mobile number already exists.") from None


async def delete(user_id: ObjectId) -> None:
    await _users().delete_one({"_id": user_id})


async def set_last_login(user_id: ObjectId) -> None:
    await _users().update_one({"_id": user_id}, {"$set": {"last_login_at": datetime.now(UTC)}})


async def list_by_role(role: str) -> list[dict]:
    return await _users().find({"role": role}).sort("created_at", -1).to_list(length=None)


async def next_sequence(name: str) -> int:
    """Atomic counter (1, 2, 3...) stored in the "counters" collection - safe even with many requests at once."""
    doc = await get_database().counters.find_one_and_update(
        {"_id": name}, {"$inc": {"value": 1}}, upsert=True, return_document=ReturnDocument.AFTER
    )
    return doc["value"]
