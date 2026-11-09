"""Staff sign-in and token refresh.

Who can sign in:
    agent    - account created by a manager (app/agents); signs in with the email/mobile + password the manager set
    manager  - account created once with: python -m scripts.create_manager
Customers don't sign in: they apply and track their application with its ID + mobile number.
"""
from app.auth.schemas import AuthResponse, LoginRequest
from app.common.enums import Role
from app.core.exceptions import Forbidden, Unauthorized
from app.core.security import REFRESH, create_access_token, create_refresh_token, decode_token, verify_password
from app.users import repository as users_repository
from app.users.schemas import UserOut
from app.users.service import ensure_can_sign_in

STAFF_ROLES = {Role.AGENT, Role.MANAGER}


def _ensure_staff(user: dict) -> None:
    """Old customer accounts from before customers stopped signing in can't open a portal any more."""
    if user["role"] not in STAFF_ROLES:
        raise Forbidden("CUSTOMER_LOGIN_DISABLED", "Customers don't need to sign in. Apply or track your loan from the home page.")


def _issue_tokens(user: dict, remember: bool) -> AuthResponse:
    user_id, role = str(user["_id"]), user["role"]
    return AuthResponse(
        access_token=create_access_token(user_id, role),
        refresh_token=create_refresh_token(user_id, role, remember),
        user=UserOut.from_doc(user),
    )


async def login(data: LoginRequest) -> AuthResponse:
    user = await users_repository.find_by_identifier(data.identifier)
    # Same message whether the account is missing or the password is wrong (don't reveal which accounts exist).
    if user is None or not verify_password(data.password, user["password_hash"]):
        raise Unauthorized("INVALID_CREDENTIALS", "Incorrect email/mobile or password.")
    _ensure_staff(user)
    ensure_can_sign_in(user)
    await users_repository.set_last_login(user["_id"])
    return _issue_tokens(user, data.remember)


async def refresh(refresh_token: str) -> AuthResponse:
    """Exchange a valid refresh token for a fresh token pair (keeps the user signed in)."""
    payload = decode_token(refresh_token, REFRESH)
    user = await users_repository.find_by_id(payload["sub"])
    if user is None:
        raise Unauthorized("INVALID_TOKEN", "Invalid session. Please sign in again.")
    _ensure_staff(user)
    ensure_can_sign_in(user)
    return _issue_tokens(user, payload.get("remember", False))
