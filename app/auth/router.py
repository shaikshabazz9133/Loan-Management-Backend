"""Customer registration and login endpoints."""

from fastapi import APIRouter, status

from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_customer(payload: RegisterRequest):
    """Create a customer account and return its access token."""
    return await AuthService().register_customer(payload)


@router.post("/login", response_model=TokenResponse)
async def login_customer(payload: LoginRequest):
    """Sign in using email address or phone number."""
    return await AuthService().login_customer(payload)
