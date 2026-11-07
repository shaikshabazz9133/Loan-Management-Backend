"""Request body for the manager's "Add new agent" form."""
from pydantic import EmailStr, Field, field_validator

from app.common.responses import CamelModel
from app.common.validators import normalize_email, normalize_mobile
from app.users.schemas import LatLng


class AgentCreate(CamelModel):
    name: str = Field(min_length=3, max_length=100)
    email: EmailStr
    mobile: str
    password: str = Field(min_length=6, max_length=128)  # the agent signs in with this
    area: str = Field(min_length=1, max_length=100)  # operating area, e.g. "Banjara Hills"
    city: str = Field(default="Hyderabad", max_length=100)
    location: LatLng  # agent sees loan requests within 2 km of this point
    active: bool = True  # inactive agents can't sign in

    @field_validator("name", "area", "city", mode="before")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalize_email(v)

    @field_validator("mobile")
    @classmethod
    def _mobile(cls, v: str) -> str:
        return normalize_mobile(v)


class AgentUpdate(CamelModel):
    """Manager edits an agent. Send only the fields that change (e.g. {"active": false} to deactivate)."""

    name: str | None = Field(default=None, min_length=3, max_length=100)
    email: EmailStr | None = None
    mobile: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)  # omit to keep the current password
    area: str | None = Field(default=None, min_length=1, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    location: LatLng | None = None
    active: bool | None = None

    @field_validator("name", "area", "city", mode="before")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        return normalize_email(v) if v else v

    @field_validator("mobile")
    @classmethod
    def _mobile(cls, v: str | None) -> str | None:
        return normalize_mobile(v) if v else v
