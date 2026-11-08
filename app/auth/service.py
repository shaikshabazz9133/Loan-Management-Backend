"""Customer registration/login business logic and JWT creation."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import HTTPException, status

from app.auth.repository import AuthRepository
from app.auth.schemas import LoginRequest, RegisterRequest
from app.core.config import AUTH, get_settings

_password_hasher = PasswordHasher()


def _public_customer(customer: dict[str, Any], customer_id: str | None = None) -> dict:
    return {
        "id": customer_id or str(customer["_id"]),
        "name": customer.get("name", ""),
        "email": customer.get("email", ""),
        "phone": customer.get("phone", ""),
    }


def _issue_token(customer_id: str) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=int(AUTH["access_token_ttl_minutes"])
    )
    return jwt.encode(
        {"sub": customer_id, "role": "customer", "exp": expires},
        settings.secret_key,
        algorithm="HS256",
    )


class AuthService:
    def __init__(self) -> None:
        self.repository = AuthRepository()

    async def register_customer(self, payload: RegisterRequest) -> dict:
        email = str(payload.email).lower()
        phone = payload.phone.strip()

        if await self.repository.email_or_phone_exists(email, phone):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with that email or phone already exists",
            )

        customer = {
            "role": "customer",
            "name": payload.name.strip(),
            "email": email,
            "phone": phone,
            "password_hash": _password_hasher.hash(payload.password),
            "active": True,
            "created_at": datetime.now(timezone.utc),
        }
        customer_id = await self.repository.create_customer(customer)
        return {
            "access_token": _issue_token(customer_id),
            "token_type": "bearer",
            "role": "customer",
            "customer": _public_customer(customer, customer_id),
        }

    async def login_customer(self, payload: LoginRequest) -> dict:
        identifier = payload.identifier.strip()
        if "@" in identifier:
            identifier = identifier.lower()

        customer = await self.repository.find_by_email_or_phone(identifier)
        invalid_credentials = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/phone or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

        if (
            customer is None
            or customer.get("role", "").lower() != "customer"
            or not customer.get("active", True)
        ):
            raise invalid_credentials

        try:
            _password_hasher.verify(
                customer.get("password_hash", ""),
                payload.password,
            )
        except (VerifyMismatchError, InvalidHashError):
            raise invalid_credentials

        customer_id = str(customer["_id"])
        return {
            "access_token": _issue_token(customer_id),
            "token_type": "bearer",
            "role": "customer",
            "customer": _public_customer(customer, customer_id),
        }
