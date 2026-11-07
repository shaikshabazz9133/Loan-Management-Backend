"""Create the manager account (run once). Safe to run again: it skips if the email or mobile already exists.

    python -m scripts.create_manager

The login details are read from .env (never committed), so no real credentials live in the code:
    MANAGER_EMAIL, MANAGER_MOBILE, MANAGER_PASSWORD   (MANAGER_NAME is optional)
"""
import asyncio
import os
import sys

from dotenv import load_dotenv

from app.common.enums import Role
from app.common.validators import normalize_email, normalize_mobile
from app.db import mongo
from app.db.indexes import create_indexes
from app.users import repository as users_repository
from app.users.models import new_user


async def main() -> None:
    load_dotenv()  # read .env like the app does
    missing = [k for k in ("MANAGER_EMAIL", "MANAGER_MOBILE", "MANAGER_PASSWORD") if not os.getenv(k)]
    if missing or os.getenv("MANAGER_PASSWORD") == "change-me":
        sys.exit(f"Set {', '.join(missing) or 'MANAGER_PASSWORD'} in .env first (see .env.example).")
    name = os.getenv("MANAGER_NAME", "Branch Manager")
    email = normalize_email(os.environ["MANAGER_EMAIL"])
    mobile = normalize_mobile(os.environ["MANAGER_MOBILE"])
    password = os.environ["MANAGER_PASSWORD"]

    await mongo.connect()
    try:
        await create_indexes(mongo.get_database())
        if await users_repository.find_by_email(email) or await users_repository.find_by_mobile(mobile):
            print(f"Manager already exists ({email} / {mobile}). Nothing to do.")
            return
        await users_repository.insert(new_user(role=Role.MANAGER, name=name, email=email, mobile=mobile,
                                               password=password))
        print(f"Manager created.\n  Email:    {email}\n  Mobile:   {mobile}\n  Password: {password}")
    finally:
        await mongo.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
