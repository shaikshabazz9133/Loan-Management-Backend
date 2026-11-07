"""Password hashing and JWT tokens.

- Passwords are stored only as Argon2 hashes (never plain text).
- Login returns two tokens:
    access token  - short-lived (15 min), sent on every request:  Authorization: Bearer <token>
    refresh token - long-lived, used only on POST /auth/refresh to get a new pair.
      "Remember me" on  -> 30 days;  off -> 1 day.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import AUTH, get_settings
from app.core.exceptions import Unauthorized

ACCESS = "access"
REFRESH = "refresh"
_ALGORITHM = "HS256"
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def _create_token(claims: dict[str, Any], lifetime: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {**claims, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, get_settings().secret_key, algorithm=_ALGORITHM)


def create_access_token(user_id: str, role: str) -> str:
    return _create_token({"sub": user_id, "role": role, "type": ACCESS},
                         timedelta(minutes=AUTH["access_token_ttl_minutes"]))


def create_refresh_token(user_id: str, role: str, remember: bool) -> str:
    days = AUTH["remember_me_ttl_days"] if remember else AUTH["refresh_token_ttl_days"]
    return _create_token({"sub": user_id, "role": role, "type": REFRESH, "remember": remember}, timedelta(days=days))


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """Return the token payload, or raise 401 if it is invalid, expired or the wrong type."""
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise Unauthorized("TOKEN_EXPIRED", "Your session has expired. Please sign in again.") from None
    except jwt.InvalidTokenError:
        raise Unauthorized("INVALID_TOKEN", "Invalid session. Please sign in again.") from None
    if payload.get("type") != expected_type:
        raise Unauthorized("INVALID_TOKEN", "Invalid session. Please sign in again.")
    return payload
