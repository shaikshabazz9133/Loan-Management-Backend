"""M2 Users & Profile  |  2 APIs
Shared user accounts (customer, agent, manager) and the signed-in user's own profile.

Endpoints to implement (thin handlers -> service layer):
    GET    /api/v1/auth/me                                     [Any]  (reusable)
        Current user, role and permissions
    PATCH  /api/v1/auth/me                                     [Any]  (reusable)
        Update own profile (mobile change needs OTP)
"""
from fastapi import APIRouter

router = APIRouter(tags=["Users & Profile"])
