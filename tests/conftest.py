"""Shared test fixtures. Tests use an in-memory MongoDB (mongomock), so no database is needed.

Run from the backend folder:  pytest -v
"""
import os

os.environ["SECRET_KEY"] = "test-secret-key-only-used-by-the-test-suite-0123456789"

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

from app.common.enums import Role  # noqa: E402
from app.db import mongo  # noqa: E402
from app.main import app  # noqa: E402
from app.users import repository  # noqa: E402
from app.users.models import new_user  # noqa: E402

MANAGER = {"email": "manager@test.com", "mobile": "9000000001", "password": "Manager@123"}


@pytest_asyncio.fixture
async def client(monkeypatch):
    """HTTP client for the API with a fresh, empty in-memory database for each test."""
    monkeypatch.setattr(mongo, "_client", AsyncMongoMockClient(tz_aware=True))
    db = mongo.get_database()
    await db.users.create_index("email", unique=True)
    await db.users.create_index("mobile", unique=True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as c:
        yield c


@pytest_asyncio.fixture
async def manager_headers(client) -> dict:
    """Create the manager (like scripts/create_manager.py does), sign in, return the auth header."""
    await repository.insert(new_user(role=Role.MANAGER, name="Test Manager", email=MANAGER["email"],
                                     mobile=MANAGER["mobile"], password=MANAGER["password"]))
    res = await client.post("/auth/login", json={"identifier": MANAGER["email"], "password": MANAGER["password"]})
    return {"Authorization": f"Bearer {res.json()['accessToken']}"}
