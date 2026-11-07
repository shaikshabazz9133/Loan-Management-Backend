"""M8 Agent Verification & Review  |  Owner: Manar  |  7 APIs
Field/document checks, credit check, comments, recommend or reject.

Endpoints to implement (thin handlers -> service layer):
    POST   /api/v1/applications/{id}/verification/start        [Agent]
        Move to in-verification
    PATCH  /api/v1/applications/{id}/verification/checks       [Agent]
        Tick field and document checks
    POST   /api/v1/applications/{id}/credit-check              [Agent]
        Credit bureau pull once (async); stores score
    POST   /api/v1/applications/{id}/comments                  [Agent]
        Add verification comment
    GET    /api/v1/applications/{id}/comments                  [Agent, Manager]  (reusable)
        List verification comments
    POST   /api/v1/applications/{id}/recommend                 [Agent]
        Recommend to manager (credit >= 650 and all checks done)
    POST   /api/v1/applications/{id}/agent-reject              [Agent]
        Reject with mandatory reason
"""
from fastapi import APIRouter

router = APIRouter(tags=["Agent Verification & Review"])
