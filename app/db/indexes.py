"""All MongoDB indexes in one place. Runs on every startup (creating an index that exists is a no-op).

users: one collection for customers, agents and managers (the "role" field tells them apart).
  - email and mobile are unique, so two accounts can never share them (even under a race).
  - location is a 2dsphere index for "agents within 2 km" queries.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.users.create_index("email", unique=True)
    await db.users.create_index("mobile", unique=True)
    await db.users.create_index([("role", 1), ("active", 1)])
    await db.users.create_index([("location", "2dsphere")])
