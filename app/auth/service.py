"""Sign-up, sign-in and token refresh logic.

Who can sign in:
    customer - creates their own account with register()
    agent    - account created by a manager (app/agents); signs in with the email/mobile + password the manager set
    manager  - account created once with: python -m scripts.create_manager
"""
from datetime import UTC, datetime

from app.auth.schemas import AuthResponse, LoginRequest, RegisterRequest
from app.common.enums import Role
from app.core.exceptions import Unauthorized
from app.core.security import REFRESH, create_access_token, create_refresh_token, decode_token, verify_password
from app.users import repository as users_repository
from app.users.models import new_user
from app.users.schemas import UserOut
from app.users.service import ensure_can_sign_in, ensure_email_and_mobile_free


def _issue_tokens(user: dict, remember: bool) -> AuthResponse:
    user_id, role = str(user["_id"]), user["role"]
    return AuthResponse(
        access_token=create_access_token(user_id, role),
        refresh_token=create_refresh_token(user_id, role, remember),
        user=UserOut.from_doc(user),
    )


async def register(data: RegisterRequest) -> AuthResponse:
    """Create a customer account and sign them in straight away."""
    await ensure_email_and_mobile_free(data.email, data.mobile)
    user = await users_repository.insert(new_user(
        role=Role.CUSTOMER,
        name=data.name,
        email=data.email,
        mobile=data.mobile,
        password=data.password,
        terms_accepted_at=datetime.now(UTC),
    ))
    return _issue_tokens(user, remember=True)


async def login(data: LoginRequest) -> AuthResponse:
    user = await users_repository.find_by_identifier(data.identifier)
    # Same message whether the account is missing or the password is wrong (don't reveal which accounts exist).
    if user is None or not verify_password(data.password, user["password_hash"]):
        raise Unauthorized("INVALID_CREDENTIALS", "Incorrect email/mobile or password.")
    ensure_can_sign_in(user)
    await users_repository.set_last_login(user["_id"])
    return _issue_tokens(user, data.remember)


async def refresh(refresh_token: str) -> AuthResponse:
    """Exchange a valid refresh token for a fresh token pair (keeps the user signed in)."""
    payload = decode_token(refresh_token, REFRESH)
    user = await users_repository.find_by_id(payload["sub"])
    if user is None:
        raise Unauthorized("INVALID_TOKEN", "Invalid session. Please sign in again.")
    ensure_can_sign_in(user)
    return _issue_tokens(user, payload.get("remember", False))
