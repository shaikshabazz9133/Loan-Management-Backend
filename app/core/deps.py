"""Reusable FastAPI dependencies.

    user: dict = Depends(get_current_user)   # any signed-in user
For role checks use app/core/permissions.py -> require_roles(Role.MANAGER).
"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import Unauthorized
from app.core.security import ACCESS, decode_token
from app.users import repository as users_repository
from app.users.service import ensure_can_sign_in

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    """Read the Bearer access token, load the user from MongoDB and make sure they may still use the app."""
    if credentials is None:
        raise Unauthorized("NOT_AUTHENTICATED", "Please sign in to continue.")
    payload = decode_token(credentials.credentials, ACCESS)
    user = await users_repository.find_by_id(payload["sub"])
    if user is None:
        raise Unauthorized("INVALID_TOKEN", "Invalid session. Please sign in again.")
    ensure_can_sign_in(user)  # e.g. an agent deactivated after login is blocked immediately
    return user
