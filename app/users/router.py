"""M2 Users & Profile

Done:
    GET    /api/v1/auth/me            [Any]   Current signed-in user (used on page refresh to restore the session)

To do:
    PATCH  /api/v1/auth/me            [Any]   Update own profile (mobile change needs OTP)
"""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.users.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["Users & Profile"])


@router.get("/me", response_model=UserOut, response_model_exclude_none=True)
async def me(user: dict = Depends(get_current_user)) -> UserOut:
    return UserOut.from_doc(user)
