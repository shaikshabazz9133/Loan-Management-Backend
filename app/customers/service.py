"""Customers are derived from applications (one customer per mobile number), so a person shows up for the
manager the moment they submit their first application."""
from app.customers.schemas import CustomerOut
from app.loans import repository as loans_repository


async def list_customers() -> list[CustomerOut]:
    customers: dict[str, dict] = {}
    for app in reversed(await loans_repository.find({})):  # oldest first, so the latest name/email wins
        c = customers.setdefault(app["mobile"], {"id": app["mobile"], "mobile": app["mobile"], "applications": 0,
                                                 "created_at": app["created_at"]})
        c.update(name=app["full_name"], email=app["email"], last_applied_at=app["created_at"])
        c["applications"] += 1
    return sorted((CustomerOut(**c) for c in customers.values()), key=lambda c: c.last_applied_at, reverse=True)
