"""M3 Customer Management

Done:
    GET    /api/v1/customers                                   [Manager]  Everyone who has applied, latest first
        (customers have no account: one customer per mobile number, built from their applications)
"""
from fastapi import APIRouter, Depends

from app.common.enums import Role
from app.core.permissions import require_roles
from app.customers import service
from app.customers.schemas import CustomerOut

router = APIRouter(prefix="/customers", tags=["Customer Management"])


@router.get("", response_model=list[CustomerOut])
async def list_customers(_: dict = Depends(require_roles(Role.MANAGER))) -> list[CustomerOut]:
    return await service.list_customers()
