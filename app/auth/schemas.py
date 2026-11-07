"""Request and response bodies for sign-up, sign-in and token refresh."""
from pydantic import EmailStr, Field, field_validator

from app.common.responses import CamelModel
from app.common.validators import normalize_email, normalize_mobile
from app.users.schemas import UserOut


class RegisterRequest(CamelModel):
    """Customer "Create your account" form."""

    name: str = Field(min_length=3, max_length=100)
    email: EmailStr
    mobile: str
    password: str = Field(min_length=8, max_length=128)
    terms_accepted: bool

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalize_email(v)

    @field_validator("mobile")
    @classmethod
    def _mobile(cls, v: str) -> str:
        return normalize_mobile(v)

    @field_validator("terms_accepted")
    @classmethod
    def _terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the terms and conditions.")
        return v


class LoginRequest(CamelModel):
    """'Welcome back' form. identifier = email or mobile number."""

    identifier: str = Field(min_length=1)
    password: str = Field(min_length=1)
    remember: bool = True


class RefreshRequest(CamelModel):
    refresh_token: str


class AuthResponse(CamelModel):
    """Returned by register, login and refresh. user.role tells the frontend which portal to open."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
