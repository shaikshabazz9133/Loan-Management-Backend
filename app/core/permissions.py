"""JWT role dependencies shared by API routers."""

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError

from app.core.config import get_settings

_bearer = HTTPBearer(auto_error=False)


def require_roles(*roles: str) -> Callable:
    """Require a valid JWT with one of the specified roles."""
    accepted = {role.lower() for role in roles}

    async def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> dict:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer token required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = jwt.decode(
                credentials.credentials,
                get_settings().secret_key,
                algorithms=["HS256"],
            )
        except InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        role = str(payload.get("role", "")).lower()
        if not payload.get("sub") or role not in accepted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return payload

    return dependency