"""MongoDB connection (Motor) and Beanie ODM initialisation.
"""
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings

_client: AsyncIOMotorClient | None = None


async def connect() -> None:
    global _client
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongodb_uri, uuidRepresentation="standard", tz_aware=True)
    # TODO: register Beanie document models here once they exist
    # await init_beanie(database=_client[settings.mongodb_db], document_models=[...])


async def disconnect() -> None:
    if _client is not None:
        _client.close()


def get_database():
    assert _client is not None, "Mongo client not initialised"
    return _client[get_settings().mongodb_db]
