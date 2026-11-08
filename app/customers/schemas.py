"""Schemas for customer self-service endpoints."""

from datetime import datetime
from pydantic import BaseModel, EmailStr


class CustomerDashboardResponse(BaseModel):
    customer_id: str
    name: str
    total_applications: int
    in_progress: int
    approved: int
    rejected: int


class CustomerApplicationItem(BaseModel):
    id: str
    amount: float
    purpose: str
    income: float
    employment: str | None = None
    city: str
    status: str
    agent_id: str | None = None
    agent_name: str | None = None
    created_at: datetime


class CustomerApplicationsPage(BaseModel):
    items: list[CustomerApplicationItem]
    total: int
    page: int
    page_size: int


class CustomerDocumentItem(BaseModel):
    id: str
    loan_id: str | None = None
    document_type: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
