"""M5 Eligibility, KYC & Rules

Done:
    POST   /api/v1/eligibility/quote                           [Public]
        Simulated CIBIL score for a PAN; with amount + income + tenure also the interest rate, EMI and totals.
        Rate = risk points from credit score, income and tenure (BUSINESS_RULES["pricing"] in core/config.py).
    (Form master data is served by GET /api/v1/applications/options.)

To do:
    PUT    /api/v1/config                                      [Manager]  Update business rules (versioned, audited)
    POST   /api/v1/kyc/aadhaar/validate, /kyc/pan/validate     [Customer] Provider-backed KYC
    GET    /api/v1/kyc/ifsc/{ifsc}                             [Any]      Bank and branch lookup
    POST   /api/v1/kyc/bank/verify                             [Customer, Manager]  Penny-drop verification
"""
from fastapi import APIRouter

from app.eligibility import service
from app.eligibility.schemas import QuoteOut, QuoteRequest

router = APIRouter(prefix="/eligibility", tags=["Eligibility, KYC & Rules"])


@router.post("/quote", response_model=QuoteOut, response_model_exclude_none=True)
async def quote(data: QuoteRequest) -> QuoteOut:
    """POST (not GET) so the PAN never appears in URLs or access logs."""
    return service.quote(data)
