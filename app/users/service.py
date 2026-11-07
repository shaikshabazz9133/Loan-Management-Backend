"""Rules about user accounts that several modules share (auth sign-up and manager "add agent")."""
from bson import ObjectId

from app.common.enums import Role
from app.core.exceptions import Conflict, Forbidden
from app.users import repository


async def ensure_email_and_mobile_free(email: str | None, mobile: str | None, except_id: ObjectId | None = None) -> None:
    """except_id: the user being edited (they may keep their own email/mobile)."""
    if email and (user := await repository.find_by_email(email)) and user["_id"] != except_id:
        raise Conflict("EMAIL_TAKEN", "An account with this email already exists.")
    if mobile and (user := await repository.find_by_mobile(mobile)) and user["_id"] != except_id:
        raise Conflict("MOBILE_TAKEN", "An account with this mobile number already exists.")


def ensure_can_sign_in(user: dict) -> None:
    """Deactivated accounts are blocked at login and on every request."""
    if user.get("active", True):
        return
    if user["role"] == Role.AGENT:
        raise Forbidden("ACCOUNT_INACTIVE", "Your agent account is deactivated. Please contact your manager.")
    raise Forbidden("ACCOUNT_INACTIVE", "Your account is blocked. Please contact support.")
