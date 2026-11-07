"""The user object returned to the frontend (camelCase JSON). Never includes the password hash."""
from datetime import datetime

from pydantic import Field

from app.common.responses import CamelModel


class LatLng(CamelModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class UserOut(CamelModel):
    id: str
    role: str
    name: str
    email: str
    mobile: str
    active: bool
    created_at: datetime
    last_login_at: datetime | None = None
    # agent-only (left out of the JSON for customers and managers)
    employee_code: str | None = None
    area: str | None = None
    city: str | None = None
    location: LatLng | None = None

    @classmethod
    def from_doc(cls, doc: dict) -> "UserOut":
        location = None
        if doc.get("location"):
            lng, lat = doc["location"]["coordinates"]
            location = LatLng(lat=lat, lng=lng)
        return cls(
            id=str(doc["_id"]),
            role=doc["role"],
            name=doc["name"],
            email=doc["email"],
            mobile=doc["mobile"],
            active=doc.get("active", True),
            created_at=doc["created_at"],
            last_login_at=doc.get("last_login_at"),
            employee_code=doc.get("employee_code"),
            area=doc.get("area"),
            city=doc.get("city"),
            location=location,
        )
