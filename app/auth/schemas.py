"""Request and response bodies for staff sign-in and token refresh."""
from pydantic import Field

from app.common.responses import CamelModel
from app.users.schemas import UserOut


class LoginRequest(CamelModel):
    """'Welcome back' form. identifier = email or mobile number."""

    identifier: str = Field(min_length=1)
    password: str = Field(min_length=1)
    remember: bool = True


class RefreshRequest(CamelModel):
    refresh_token: str


class AuthResponse(CamelModel):
    """Returned by login and refresh. user.role tells the frontend which portal to open."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
