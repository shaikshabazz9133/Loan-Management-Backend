"""MongoDB queries for loan applications and their uploaded files. No business rules here."""
from typing import Any

from bson import Binary, ObjectId
from pymongo import ReturnDocument

from app.db.mongo import get_database
from app.loans.models import history_entry
from app.loans.state_machine import ASSIGNED, UNASSIGNED


def _applications():
    return get_database().applications


def _files():
    return get_database().application_files


async def insert(application: dict[str, Any]) -> dict[str, Any]:
    await _applications().insert_one(application)
    return application


async def find_by_id(application_id: str) -> dict | None:
    return await _applications().find_one({"_id": application_id})


async def find(query: dict[str, Any]) -> list[dict]:
    """Newest first."""
    return await _applications().find(query).sort("created_at", -1).to_list(length=None)


async def insert_files(files: list[dict[str, Any]]) -> list[ObjectId]:
    if not files:
        return []
    docs = [{**f, "data": Binary(f["data"])} for f in files]
    result = await _files().insert_many(docs)
    return list(result.inserted_ids)


async def delete_files(file_ids: list[ObjectId]) -> None:
    if file_ids:
        await _files().delete_many({"_id": {"$in": file_ids}})


async def find_file(file_id: ObjectId) -> dict | None:
    return await _files().find_one({"_id": file_id})


async def count(query: dict[str, Any]) -> int:
    return await _applications().count_documents(query)


async def transition(application_id: str, match: dict[str, Any], changes: dict[str, Any],
                     history: dict[str, Any]) -> dict | None:
    """Atomically apply a status change only if the application still matches (e.g. still unassigned).
    Returns the updated document, or None if someone else changed it first."""
    return await _applications().find_one_and_update(
        {"_id": application_id, **match},
        {"$set": changes, "$push": {"history": history}},
        return_document=ReturnDocument.AFTER,
    )


async def release_agent_applications(agent_id: ObjectId, now) -> None:
    """A deactivated agent's accepted (not yet decided) applications go back to the open pool."""
    await _applications().update_many(
        {"agent_id": agent_id, "status": ASSIGNED},
        {"$set": {"status": UNASSIGNED, "agent_id": None, "agent_name": None, "updated_at": now},
         "$push": {"history": history_entry(now, None, "Returned to open applications", "The agent was deactivated")}},
    )
