"""M3 Customer Management

Done:
    GET    /api/v1/customers                                   [Manager]  Every registered customer, newest first
        (a customer appears here as soon as they sign up; application stats are worked out from GET /applications)

To do:
    PATCH  /api/v1/customers/{id}/status                       [Manager]  Block / unblock customer
"""
from fastapi import APIRouter, Depends

from app.common.enums import Role
from app.core.permissions import require_roles
from app.customers import service
from app.users.schemas import UserOut

router = APIRouter(prefix="/customers", tags=["Customer Management"])


@router.get("", response_model=list[UserOut], response_model_exclude_none=True)
async def list_customers(_: dict = Depends(require_roles(Role.MANAGER))) -> list[UserOut]:
    return await service.list_customers()
