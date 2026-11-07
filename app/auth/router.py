"""M1 Authentication  |  Owner: Soughat  |  9 APIs
Sign-up, login (email or mobile), JWT access/refresh rotation, OTP, password reset.

Endpoints to implement (thin handlers -> service layer):
    POST   /api/v1/auth/register                               [Public]
        Customer sign-up (name, email, mobile, password, terms)
    POST   /api/v1/auth/login                                  [Public]  (reusable)
        Login with email or mobile; returns tokens + role for redirect
    POST   /api/v1/auth/refresh                                [Public]  (reusable)
        Rotate access/refresh tokens (refresh-token reuse detection)
    POST   /api/v1/auth/logout                                 [Any]  (reusable)
        Revoke current refresh token / session
    POST   /api/v1/auth/otp/send                               [Public]  (reusable)
        Send OTP to mobile (sign-up verification, reset)
    POST   /api/v1/auth/otp/verify                             [Public]  (reusable)
        Verify OTP and return a short-lived verification token
    POST   /api/v1/auth/forgot-password                        [Public]  (reusable)
        Start password reset (same response whether or not user exists)
    POST   /api/v1/auth/reset-password                         [Public]  (reusable)
        Set new password using reset token
    POST   /api/v1/auth/change-password                        [Any]  (reusable)
        Change password when logged in
"""
from fastapi import APIRouter

router = APIRouter(tags=["Authentication"])
