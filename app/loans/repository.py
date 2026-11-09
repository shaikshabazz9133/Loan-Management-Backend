"""MongoDB queries for loan applications and their uploaded files. No business rules here."""
from typing import Any

from bson import Binary, ObjectId

from app.db.mongo import get_database


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
