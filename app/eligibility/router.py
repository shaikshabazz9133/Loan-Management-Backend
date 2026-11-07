"""M5 Eligibility, KYC & Rules  |  7 APIs
Aadhaar, PAN, IFSC and bank validation; business-rule configuration and the EMI calculator.

Endpoints to implement (thin handlers -> service layer):
    GET    /api/v1/config                                      [Any]  (reusable)
        Master data - loan purposes, employment types, tenures, rate, radius, min credit score
    PUT    /api/v1/config                                      [Manager]
        Update business rules (versioned, audited)
    GET    /api/v1/config/emi                                  [Any]  (reusable)
        EMI calculator (amount, tenure) - used by apply form and agent view
    POST   /api/v1/kyc/aadhaar/validate                        [Customer]  (reusable)
        Format + Verhoeff checksum; optional OTP e-KYC via provider
    POST   /api/v1/kyc/pan/validate                            [Customer]  (reusable)
        Format + PAN status/name match via provider
    GET    /api/v1/kyc/ifsc/{ifsc}                             [Any]  (reusable)
        Bank and branch lookup (cached in Redis)
    POST   /api/v1/kyc/bank/verify                             [Customer, Manager]  (reusable)
        Penny-drop account verification and holder-name match
"""
from fastapi import APIRouter

router = APIRouter(tags=["Eligibility, KYC & Rules"])
