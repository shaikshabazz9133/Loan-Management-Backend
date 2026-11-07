"""M9 Manager Decisions & Disbursement  |  Owner: Shabazz  |  6 APIs
Final approval/rejection and payout to the verified bank account.

Endpoints to implement (thin handlers -> service layer):
    POST   /api/v1/applications/{id}/approve                   [Manager]
        Final approval (only after agent recommendation and credit >= 650)
    POST   /api/v1/applications/{id}/reject                    [Manager]
        Final rejection with mandatory reason
    POST   /api/v1/applications/{id}/disburse                  [Manager]
        Payout via IMPS/NEFT/RTGS; Idempotency-Key; returns UTR
    GET    /api/v1/disbursements                               [Manager]
        List payouts with status and filters
    GET    /api/v1/disbursements/{id}                          [Customer, Manager]  (reusable)
        Disbursement receipt
    POST   /api/v1/webhooks/payouts                            [Provider]
        HMAC-signed payout status callback (UTR, success/failure)
"""
from fastapi import APIRouter

router = APIRouter(tags=["Manager Decisions & Disbursement"])
