"""M1 Authentication

Done:
    POST   /api/v1/auth/register          [Public]  Customer sign-up -> returns tokens (signed in right away)
    POST   /api/v1/auth/login             [Public]  Sign in with email or mobile -> tokens + user (role)
    POST   /api/v1/auth/refresh           [Public]  New token pair from a refresh token

To do:
    POST   /api/v1/auth/logout                      Revoke refresh token (frontend can simply delete tokens for now)
    POST   /api/v1/auth/otp/send, /otp/verify       Mobile OTP
    POST   /api/v1/auth/forgot-password, /reset-password   Needs an email/SMS provider
    POST   /api/v1/auth/change-password             Change password when logged in
"""
from fastapi import APIRouter, status

from app.auth import service
from app.auth.schemas import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, response_model_exclude_none=True,
             status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest) -> AuthResponse:
    return await service.register(data)


@router.post("/login", response_model=AuthResponse, response_model_exclude_none=True)
async def login(data: LoginRequest) -> AuthResponse:
    return await service.login(data)


@router.post("/refresh", response_model=AuthResponse, response_model_exclude_none=True)
async def refresh(data: RefreshRequest) -> AuthResponse:
    return await service.refresh(data.refresh_token)
