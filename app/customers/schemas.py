"""A customer as the manager sees them. Customers have no account: they are the people who applied,
grouped by mobile number."""
from datetime import datetime

from app.common.responses import CamelModel


class CustomerOut(CamelModel):
    id: str  # mobile number
    role: str = "customer"
    name: str
    email: str
    mobile: str
    applications: int
    created_at: datetime  # first application
    last_applied_at: datetime
