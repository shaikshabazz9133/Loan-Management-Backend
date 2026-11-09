"""M1 Authentication

Done:
    POST   /api/v1/auth/login             [Public]  Agent / manager sign in with email or mobile -> tokens + user (role)
    POST   /api/v1/auth/refresh           [Public]  New token pair from a refresh token

Customers do not have accounts: they apply and track their application without signing in (see app/loans).

To do:
    POST   /api/v1/auth/logout                      Revoke refresh token (frontend can simply delete tokens for now)
    POST   /api/v1/auth/otp/send, /otp/verify       Mobile OTP
    POST   /api/v1/auth/forgot-password, /reset-password   Needs an email/SMS provider
    POST   /api/v1/auth/change-password             Change password when logged in
"""
from fastapi import APIRouter

from app.auth import service
from app.auth.schemas import AuthResponse, LoginRequest, RefreshRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=AuthResponse, response_model_exclude_none=True)
async def login(data: LoginRequest) -> AuthResponse:
    return await service.login(data)


@router.post("/refresh", response_model=AuthResponse, response_model_exclude_none=True)
async def refresh(data: RefreshRequest) -> AuthResponse:
    return await service.refresh(data.refresh_token)
