"""Customer loan application endpoints."""

import csv
import io

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.core.permissions import require_roles
from app.loans.schemas import LoanApplicationCreate, LoanApplicationPage
from app.loans.service import LoanService

router = APIRouter(prefix="/loans", tags=["Customer Loans"])
customer_access = Depends(require_roles("customer"))


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_loan_application(
    payload: LoanApplicationCreate,
    current_user: dict = customer_access,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Submit a loan application for the authenticated customer."""
    return await LoanService().create_application(
        current_user, payload, idempotency_key=idempotency_key
    )


@router.get("/my-applications", response_model=LoanApplicationPage)
async def my_loan_applications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = customer_access,
):
    """Return the authenticated customer's paginated loan history."""
    return await LoanService().list_my_applications(
        current_user, page=page, page_size=page_size
    )


@router.get("/{loan_id}/timeline")
async def loan_timeline(loan_id: str, current_user: dict = customer_access):
    return await LoanService().timeline(current_user, loan_id)


@router.get("/{loan_id}/assignment")
async def loan_assignment(loan_id: str, current_user: dict = customer_access):
    return await LoanService().assignment(current_user, loan_id)


@router.post("/{loan_id}/cancel")
async def cancel_loan(loan_id: str, current_user: dict = customer_access):
    return await LoanService().cancel(current_user, loan_id)


@router.get("/{loan_id}/export")
async def export_loan(loan_id: str, current_user: dict = customer_access):
    record = await LoanService().get_application(current_user, loan_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Field", "Value"])
    for field in (
        "id", "name", "email", "phone", "amount", "purpose", "income",
        "employment", "address", "city", "pincode", "status", "created_at",
    ):
        writer.writerow([field, record.get(field, "")])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="loan-{loan_id}.csv"'
        },
    )


@router.get("/{loan_id}")
async def get_loan(loan_id: str, current_user: dict = customer_access):
    """Read a loan application owned by the authenticated customer."""
    return await LoanService().get_application(current_user, loan_id)
