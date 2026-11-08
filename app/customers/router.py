"""Customer self-service dashboard and own application/document views."""

from fastapi import APIRouter, Depends, Query

from app.core.permissions import require_roles
from app.customers.schemas import (
    CustomerApplicationsPage,
    CustomerDashboardResponse,
    CustomerDocumentItem,
)
from app.customers.service import CustomerService

router = APIRouter(prefix="/customers", tags=["Customer"])
customer_access = Depends(require_roles("customer"))


@router.get("/dashboard", response_model=CustomerDashboardResponse)
async def customer_dashboard(current_user: dict = customer_access):
    """Get the authenticated customer's dashboard summary."""
    return await CustomerService().dashboard(current_user)


@router.get("/me/applications", response_model=CustomerApplicationsPage)
async def my_applications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = customer_access,
):
    """List only the authenticated customer's loan applications."""
    return await CustomerService().my_applications(
        current_user, page=page, page_size=page_size
    )


@router.get("/me/documents", response_model=list[CustomerDocumentItem])
async def my_documents(current_user: dict = customer_access):
    """List only the authenticated customer's uploaded documents."""
    return await CustomerService().my_documents(current_user)
