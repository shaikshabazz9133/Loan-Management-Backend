"""Request and response schemas for customer loan applications."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class LoanApplicationCreate(BaseModel):
    # Contact details are captured as an application snapshot.
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=24)
    amount: float = Field(ge=10000, le=5000000)
    purpose: str = Field(min_length=2, max_length=100)
    income: float = Field(gt=0)
    employment: str = Field(min_length=2, max_length=80)
    address: str = Field(min_length=3, max_length=300)
    city: str = Field(min_length=2, max_length=100)
    pincode: str = Field(min_length=4, max_length=12)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class LoanApplicationItem(BaseModel):
    id: str
    amount: float
    purpose: str
    income: float
    employment: str
    city: str
    status: str
    agent_id: str | None = None
    agent_name: str | None = None
    created_at: datetime


class LoanApplicationPage(BaseModel):
    items: list[LoanApplicationItem]
    total: int
    page: int
    page_size: int
