"""MongoDB connection (Motor = async MongoDB driver).

connect() runs once when the app starts, disconnect() when it stops.
Anywhere else, call get_database() and use a collection, e.g. get_database().users
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

_client: AsyncIOMotorClient | None = None


async def connect() -> None:
    global _client
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongodb_uri, uuidRepresentation="standard", tz_aware=True)
    await _client.admin.command("ping")  # fail fast on startup if the URI or password is wrong


async def disconnect() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_database() -> AsyncIOMotorDatabase:
    assert _client is not None, "MongoDB is not connected"
    return _client[get_settings().mongodb_db]
