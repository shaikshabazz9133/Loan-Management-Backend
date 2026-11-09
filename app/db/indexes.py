"""All MongoDB indexes in one place. Runs on every startup (creating an index that exists is a no-op).

users: one collection for customers, agents and managers (the "role" field tells them apart).
  - email and mobile are unique, so two accounts can never share them (even under a race).
"""
from motor.motor_asyncio import AsyncIOMotorDatabase


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.users.create_index("email", unique=True)
    await db.users.create_index("mobile", unique=True)
    await db.users.create_index([("role", 1), ("active", 1)])
    await db.applications.create_index([("customer_id", 1), ("created_at", -1)])
    await db.applications.create_index([("status", 1), ("created_at", -1)])
    await db.applications.create_index("agent_id")
    await db.application_files.create_index("application_id")
