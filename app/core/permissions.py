"""Role-based access control. Use this instead of writing role checks by hand:

    @router.post("/agents")
    async def create(..., manager: dict = Depends(require_roles(Role.MANAGER))): ...
"""
from fastapi import Depends

from app.common.enums import Role
from app.core.deps import get_current_user
from app.core.exceptions import Forbidden


def require_roles(*roles: Role):
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise Forbidden("FORBIDDEN", "You do not have permission to do this.")
        return user

    return checker
